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
    with open("config.yaml") as f:
        return yaml.load(f, Loader=yaml.FullLoader)


@app.route("/mutate", methods=["POST"])
def mutate():
    """
    receive webhook from kubernetes, modify object, generate operation
    and return AdmissionReview object
    """
    request_payload = request.json
    modified_payload = copy.deepcopy(request_payload)

    request_uid = request_payload["request"]["uid"]

    object = request_payload["request"]["object"]
    modified_object = inject_metadata(modified_payload["request"]["object"])

    operation = jsonpatch_operation(object, modified_object)
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


def base64_patch(patch):
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
        key = list(annotation.keys())[0]
        value = list(annotation.values())[0]
        if key not in object["metadata"]["annotations"].keys():
            object["metadata"]["annotations"][key] = value

    if "labels" not in object["metadata"].keys():
        object["metadata"]["labels"] = {}
    if "tmp-annotations" not in object["metadata"]["labels"].keys():
        object["metadata"]["labels"]["tmp-annotations"] = "enabled"

    return object


def jsonpatch_operation(object, modified_object):
    """
    generate JSONPatch operation from objects diff
    ref: https://python-json-patch.readthedocs.io/en/latest/tutorial.html#creating-a-patch
    """
    operation = jsonpatch.JsonPatch.from_diff(object, modified_object)
    app.logger.debug(f"JSONPatch operation generated: {operation}")
    return base64_patch(operation)


@scheduler.task("interval", id="delete_annotations", seconds=60, misfire_grace_time=900)
def delete_annotations():
    """
    remove annotations from all pods based on namespace selector which
    exist longer than "wait" threshold defined on config.yaml
    """
    config.load_incluster_config()
    internal_config = load_config()

    v1 = client.CoreV1Api()
    namespaces = v1.list_namespace(
        label_selector="tmp-annotations.io/tmp-annotations=enabled"
    ).items

    now = datetime.datetime.now(datetime.timezone.utc)
    wait = datetime.timedelta(minutes=internal_config["wait"]).total_seconds()

    for namespace in namespaces:
        pods = v1.list_namespaced_pod(
            namespace=namespace.metadata.name, label_selector="tmp-annotations=enabled"
        ).items
        for pod in pods:
            diff = (now - pod.status.start_time).total_seconds()
            if diff > wait:
                app.logger.debug(f"pod: {pod.metadata.name} | eligible")
            else:
                app.logger.debug(f"pod: {pod.metadata.name} | not eligible | diff: {diff}s")


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port="5000",
        debug="True",
        ssl_context=("server.crt", "server.key"),
    )
