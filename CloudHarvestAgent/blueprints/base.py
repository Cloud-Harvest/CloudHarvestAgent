from flask import Request

def safe_request_get_json(request: Request) -> dict:
    """
    Safely retrieves the JSON data from a request.
    :param request: The request to retrieve the JSON data from.
    :return: The JSON data from the request.
    """
    try:
        return request.get_json()

    except Exception as e:
        return {}
