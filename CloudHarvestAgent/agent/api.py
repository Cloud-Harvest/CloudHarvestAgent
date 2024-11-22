from typing import Literal
from logging import getLogger

logger = getLogger('harvest')


class Api:
    """
    Represents an Api object that can be used to make requests to the CloudHarvest API.
    """

    def __init__(self, host: str, port: int, token: str):
        self.host = host
        self.port = port
        self.token = token

    def request(self, request_type: Literal['get', 'post', 'put', 'delete'], endpoint: str, data: dict = None, **requests_kwargs) -> dict:
        """
        Makes an API request to the CloudHarvest API.

        Arguments
        host: (str) The host of the API.
        port: (int) The port of the API.
        token: (str) The token to authenticate with the API.
        request_type: (str) The type of request to make (GET, POST, PUT, DELETE).
        endpoint: (str) The endpoint to make the request to.
        data: (dict) The data to send with the request.

        Returns
        {
            'status_code': (int) The status code of the response.
            'response': (dict) The response from the API.
        }
        """

        from requests import get, post, put, delete, ConnectionError, Timeout, HTTPError, RequestException

        from uuid import uuid4
        request_id = str(uuid4())

        request_types = {
            'get': get,
            'post': post,
            'put': put,
            'delete': delete
        }

        response = None

        try:
            logger.debug(f'request:{request_id}: {self.host}:{self.port}/{endpoint}')
            response = request_types[request_type](f'https://{self.host}:{self.port}/{endpoint}',
                                                   headers={'Authorization': f'Bearer {self.token}'},
                                                   json=data,
                                                   **requests_kwargs)

        except ConnectionError as e:
            logger.error(f'request:{request_id}:Connection error occurred: {e}')

        except Timeout as e:
            logger.error(f'request:{request_id}:Timed out: {e}')

        except HTTPError as e:
            logger.error(f'request:{request_id}:HTTP error occurred: {e}')

        except RequestException as e:
            logger.error(f'request:{request_id}:Error making API request: {e}')

        except Exception as e:
            logger.error(f'request:{request_id}:An unexpected error occurred: {e}')

        return {
            'status_code': response.status_code,
            'response': response.json()
        }
