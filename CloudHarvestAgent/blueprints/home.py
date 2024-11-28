"""
The home blueprint for the Harvest Agent. It handles the root endpoint and error handling.
"""

from .base import HarvestBlueprint
from flask import Response, jsonify

home_blueprint = HarvestBlueprint(
    'home_bp', __name__
)


@home_blueprint.route(rule='/', methods=['GET'])
def home() -> Response:
    """
    The root endpoint for the Harvest Agent.
    """

    return jsonify('Successfully reached a CloudHarvestAgent instance.')


@home_blueprint.errorhandler(400)
def bad_request_error(error):
    return jsonify({"error-code": "400", "error-message": "Bad Request"})


@home_blueprint.errorhandler(401)
def unauthorized_error(error):
    return jsonify({"error-code": "401", "error-message": "Unauthorized"})


# @home_blueprint.errorhandler(402)
# def payment_required_error(error):
#     return jsonify({"error-code": "402", "error-message": "Payment Required"})


@home_blueprint.errorhandler(403)
def forbidden_error(error):
    return jsonify({"error-code": "403", "error-message": "Forbidden"})


@home_blueprint.errorhandler(404)
def not_found_error(error):
    return jsonify({"error-code": "404", "error-message": "Not Found"})


@home_blueprint.errorhandler(405)
def method_not_allowed_error(error):
    return jsonify({"error-code": "405", "error-message": "Method Not Allowed"})


@home_blueprint.errorhandler(406)
def not_acceptable_error(error):
    return jsonify({"error-code": "406", "error-message": "Not Acceptable"})


# @home_blueprint.errorhandler(407)
# def proxy_authentication_required_error(error):
#     return jsonify({"error-code": "407", "error-message": "Proxy Authentication Required"})


@home_blueprint.errorhandler(408)
def request_timeout_error(error):
    return jsonify({"error-code": "408", "error-message": "Request Timeout"})


@home_blueprint.errorhandler(409)
def conflict_error(error):
    return jsonify({"error-code": "409", "error-message": "Conflict"})


@home_blueprint.errorhandler(410)
def gone_error(error):
    return jsonify({"error-code": "410", "error-message": "Gone"})


@home_blueprint.errorhandler(411)
def length_required_error(error):
    return jsonify({"error-code": "411", "error-message": "Length Required"})


@home_blueprint.errorhandler(412)
def precondition_failed_error(error):
    return jsonify({"error-code": "412", "error-message": "Precondition Failed"})


@home_blueprint.errorhandler(413)
def payload_too_large_error(error):
    return jsonify({"error-code": "413", "error-message": "Payload Too Large"})


@home_blueprint.errorhandler(414)
def uri_too_long_error(error):
    return jsonify({"error-code": "414", "error-message": "URI Too Long"})


@home_blueprint.errorhandler(415)
def unsupported_media_type_error(error):
    return jsonify({"error-code": "415", "error-message": "Unsupported Media Type"})


@home_blueprint.errorhandler(416)
def range_not_satisfiable_error(error):
    return jsonify({"error-code": "416", "error-message": "Range Not Satisfiable"})


@home_blueprint.errorhandler(417)
def expectation_failed_error(error):
    return jsonify({"error-code": "417", "error-message": "Expectation Failed"})


# @home_blueprint.errorhandler(426)
# def upgrade_required_error(error):
#     return jsonify({"error-code": "426", "error-message": "Upgrade Required"})


@home_blueprint.errorhandler(500)
def internal_server_error(error):
    return jsonify({"error-code": "500", "error-message": "Internal Server Error"})


@home_blueprint.errorhandler(501)
def not_implemented_error(error):
    return jsonify({"error-code": "501", "error-message": "Not Implemented"})


@home_blueprint.errorhandler(502)
def bad_gateway_error(error):
    return jsonify({"error-code": "502", "error-message": "Bad Gateway"})


@home_blueprint.errorhandler(503)
def service_unavailable_error(error):
    return jsonify({"error-code": "503", "error-message": "Service Unavailable"})


@home_blueprint.errorhandler(504)
def gateway_timeout_error(error):
    return jsonify({"error-code": "504", "error-message": "Gateway Timeout"})


@home_blueprint.errorhandler(505)
def http_version_not_supported_error(error):
    return jsonify({"error-code": "505", "error-message": "HTTP Version Not Supported"})
