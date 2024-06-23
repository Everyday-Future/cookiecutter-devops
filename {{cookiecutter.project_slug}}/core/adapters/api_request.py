import os
import httpx
from typing import Dict, Any, Optional
from httpx import RequestError
from config import logger


class RequestHandler:
    timeout = 20

    def __init__(self):
        self.timeout = int(os.getenv('REQUEST_TIMEOUT', 20))

    @staticmethod
    def validate_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean the parameters by removing unset (None) values.
        """
        return {key: val for key, val in params.items() if val is not None}

    @staticmethod
    def validate_url(url: str) -> None:
        """
        Validate the request URL.
        """
        if not url.startswith("http://") and not url.startswith("https://"):
            raise ValueError("Invalid URL. Must start with 'http://' or 'https://'.")

    @staticmethod
    def validate_response(response: httpx.Response) -> None:
        """
        Validate the response status code and content.
        """
        response.raise_for_status()  # Ensure this is called
        if 'application/json' not in response.headers.get('Content-Type', ''):
            raise ValueError("Response content is not JSON")

    @classmethod
    async def send_request(cls, request_url: str, params: Dict[str, Any], method: str = 'GET',
                           headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Send an asynchronous HTTP request and return the JSON response.

        :param request_url: The URL to send the request to.
        :param params: A dictionary of query parameters.
        :param method: The HTTP method to use (default is 'GET').
        :param headers: Optional dictionary of HTTP headers.
        :return: The JSON response as a dictionary.
        """
        cls.validate_url(request_url)
        params = cls.validate_params(params)

        async with httpx.AsyncClient(timeout=cls.timeout) as client:
            try:
                response = await client.request(method, request_url, params=params if method.upper() == 'GET' else None,
                                                json=params if method.upper() == 'POST' else None, headers=headers)
                cls.validate_response(response)
                return await response.json()
            except RequestError as e:
                logger.error(f"Request failed: {e}")
                raise

    def mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mask sensitive data in the parameters.

        :param data: A dictionary containing the parameters.
        :return: The dictionary with sensitive data masked.
        """
        sensitive_keys = {'password', 'token', 'secret'}
        return {key: ('****' if key in sensitive_keys else val) for key, val in data.items()}

    async def request_with_masking(self, request_url: str, params: Dict[str, Any], method: str = 'GET',
                                   headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Send a request with masked sensitive data.

        :param request_url: The URL to send the request to.
        :param params: A dictionary of query parameters.
        :param method: The HTTP method to use (default is 'GET').
        :param headers: Optional dictionary of HTTP headers.
        :return: The JSON response as a dictionary.
        """
        masked_params = self.mask_sensitive_data(params)
        logger.info(f"Sending request to {request_url} with params {masked_params}")
        return await self.send_request(request_url, params, method, headers)
