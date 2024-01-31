import yaml
from flask import Flask, request, jsonify
import jsonpatch
import base64
import copy
import yaml

app = Flask(__name__)

def load_config ():
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
    modified_object = inject_annotations(modified_payload["request"]["object"])

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

def inject_annotations(object):
    """inject annotations inside object key"""
    config = load_config()
    app.logger.debug(f"config: {config}")

    if "annotations" not in object["metadata"].keys():
        object["metadata"]["annotations"] = {}

    for annotation in config["annotations"]:
        key = list(annotation.keys())[0]
        value = list(annotation.values())[0]
        if key not in object["metadata"]["annotations"].keys():
            object["metadata"]["annotations"][key] = value
    return object


def jsonpatch_operation(object, modified_object):
    """
    generate JSONPatch operation from objects diff
    ref: https://python-json-patch.readthedocs.io/en/latest/tutorial.html#creating-a-patch
    """
    operation = jsonpatch.JsonPatch.from_diff(object, modified_object)
    app.logger.debug(f"JSONPatch operation generated: {operation}")
    return base64_patch(operation)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port="5000",
        debug="True",
        ssl_context=("server.crt", "server.key"),
    )
