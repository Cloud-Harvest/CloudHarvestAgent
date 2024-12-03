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

        from requests import get, post, put, delete

        from uuid import uuid4
        request_id = str(uuid4())

        response = None

        try:
            from requests.api import request
            logger.debug(f'request:{request_id}: {self.host}:{self.port}/{endpoint}')
            response = request(method=request_type,
                               url=f'https://{self.host}:{self.port}/{endpoint}',
                               headers={
                                   'Authorization': f'Bearer {self.token}'
                               },
                               json=data,
                               **requests_kwargs)

        except Exception as e:
            logger.error(f'request:{request_id}:An unexpected error occurred: {e}')

            if response:
                return {
                    'id': request_id,
                    'status_code': response.status_code,
                    'error': f'{str(e)}: {e.args}',
                    'response': response.json()
                }

            else:
                return {
                    'id': request_id,
                    'status_code': 500,
                    'error': f'{str(e)}: {e.args}',
                    'response': {}
                }

        return {
            'id': request_id,
            'status_code': response.status_code,
            'response': response.json()
        }
