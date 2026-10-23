from flask import jsonify


def success_response(
    message="Request successful.",
    data=None,
    status_code=200,
    **extra
):
    body = {
        "success": True,
        "message": message,
    }

    if data is not None:
        body["data"] = data

    body.update(extra)

    return jsonify(body), status_code


def error_response(
    message="Request failed.",
    status_code=400,
    errors=None,
    **extra
):
    body = {
        "success": False,
        "message": message,
    }

    if errors is not None:
        body["errors"] = errors

    body.update(extra)

    return jsonify(body), status_code
