from flask import Flask, request, jsonify
import jsonpatch
import base64
import copy

app = Flask(__name__)

@app.route("/mutate", methods=["POST"])
def mutate():
    request_payload = request.json
    modified_payload = copy.deepcopy(request_payload)

    request_uid = request_payload["request"]["uid"]

    object = request_payload["request"]["object"]
    modified_object = inject_annotation(modified_payload["request"]["object"])

    operation = jsonpatch_operation(object, modified_object)
    app.logger.debug(f"base64 operation generated: {operation}")

    admission_review = {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "response": {
            "uid": request_uid,
            "allowed": True,
            "patchType": "JSONPatch",
            "patch": operation
        }
    }

    return jsonify(admission_review)

def base64_patch(patch):
    return base64.b64encode(patch.to_string().encode("utf-8")).decode("utf-8")

def inject_annotation(object):
    if "annotations" not in object["metadata"].keys():
        object["metadata"]["annotations"] = {}
    if "karpenter.sh/do-not-disrupt" not in object["metadata"]["annotations"].keys():
        object["metadata"]["annotations"]["karpenter.sh/do-not-disrupt"] = "true"
    return object

def jsonpatch_operation (object, modified_object):
    operation = jsonpatch.JsonPatch.from_diff(object, modified_object)
    app.logger.debug(f"JSONPatch operation generated: {operation}")
    return base64_patch(operation)

if __name__ == '__main__':
    app.run(
        host="0.0.0.0",
        port="5000",
        debug="True",
        ssl_context=(
            'server.crt',
            'server.key'
        )
    )
