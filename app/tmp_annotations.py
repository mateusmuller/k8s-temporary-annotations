from flask import Flask, request, jsonify
from flask_apscheduler import APScheduler
from kubernetes import client, config
import datetime
import jsonpatch
import base64
import copy
import yaml

app = Flask(__name__)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()


def load_config():
    """load yaml config file in memory"""
    with open("config.yaml") as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def itself(object):
    if object["metadata"]["labels"]["app"] == "tmp-annotations":
        return True
    return False


@app.route("/mutate", methods=["POST"])
def mutate():
    """
    receive webhook from kubernetes, modify object, generate operation
    and return AdmissionReview object
    """
    request_payload = request.json
    modified_payload = copy.deepcopy(request_payload)
    request_uid = request_payload["request"]["uid"]

    if itself(request_payload["request"]["object"]):
        admission_review = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {"uid": request_uid, "allowed": True},
        }

        return jsonify(admission_review)
    else:
        object = request_payload["request"]["object"]
        modified_object = inject_metadata(modified_payload["request"]["object"])

        operation = generate_jsonpatch_operation(object, modified_object)
        app.logger.debug(f"base64 operation generated: {operation}")

        admission_review = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": request_uid,
                "allowed": True,
                "patchType": "JSONPatch",
                "patch": operation,
            },
        }

        return jsonify(admission_review)


def generate_base64_patch(patch):
    """
    convert JSONPatch operation to base64
    ref: https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/#response
    """
    return base64.b64encode(patch.to_string().encode("utf-8")).decode("utf-8")


def inject_metadata(object):
    """inject annotations and label inside object key"""
    internal_config = load_config()
    app.logger.debug(f"config: {internal_config}")

    if "annotations" not in object["metadata"].keys():
        object["metadata"]["annotations"] = {}

    for annotation in internal_config["annotations"]:
        value = internal_config["annotations"][annotation]
        if annotation not in object["metadata"]["annotations"].keys():
            object["metadata"]["annotations"][annotation] = value

    if "labels" not in object["metadata"].keys():
        object["metadata"]["labels"] = {}
    if "tmp-annotations" not in object["metadata"]["labels"].keys():
        object["metadata"]["labels"]["tmp-annotations"] = "enabled"

    return object


def generate_jsonpatch_operation(object, modified_object):
    """
    generate JSONPatch operation from objects diff
    ref: https://python-json-patch.readthedocs.io/en/latest/tutorial.html#creating-a-patch
    """
    operation = jsonpatch.JsonPatch.from_diff(object, modified_object)
    app.logger.debug(f"JSONPatch operation generated: {operation}")
    return generate_base64_patch(operation)


def generate_remove_jsonpatch_operation():
    internal_config = load_config()
    annotations = []

    for key, value in internal_config["annotations"].items():
        annotations.append(
            {
                "op": "remove",
                "path": f"/metadata/annotations/{key.replace('/','~1')}",
                "value": f"{value}",
            }
        )

    label = [
        {"op": "remove", "path": "/metadata/labels/tmp-annotations", "value": "enabled"}
    ]

    return annotations + label


@scheduler.task("interval", id="remove_metadata", seconds=60)
def remove_metadata():
    """
    remove annotations from all pods based on namespace selector which
    exist longer than "wait" thresh old defined on config.yaml
    """
    config.load_incluster_config()
    internal_config = load_config()

    v1 = client.CoreV1Api()
    namespaces = v1.list_namespace(label_selector="tmp-annotations=enabled").items

    now = datetime.datetime.now(datetime.timezone.utc)
    wait = datetime.timedelta(minutes=internal_config["wait"]).total_seconds()

    for namespace in namespaces:
        pods = v1.list_namespaced_pod(
            namespace=namespace.metadata.name,
            label_selector="tmp-annotations=enabled,app!=tmp-annotations",
        ).items
        for pod in pods:
            diff = (now - pod.status.start_time).total_seconds()
            if diff > wait:
                app.logger.debug(f"pod: {pod.metadata.name} | eligible | patching...")
                v1.patch_namespaced_pod(
                    name=pod.metadata.name,
                    namespace=namespace.metadata.name,
                    body=generate_remove_jsonpatch_operation(),
                )
            else:
                app.logger.debug(
                    f"pod: {pod.metadata.name} | not eligible | diff: {diff}s"
                )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port="5000",
        debug=True,
        use_reloader=False,
        ssl_context=("server.crt", "server.key"),
    )
