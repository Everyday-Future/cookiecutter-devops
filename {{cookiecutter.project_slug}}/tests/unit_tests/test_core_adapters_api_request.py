import pytest
import httpx
from httpx import RequestError, HTTPStatusError
from unittest.mock import patch, AsyncMock
from core.adapters.api_request import RequestHandler  # Adjust the import based on your file structure


@pytest.fixture
def handler():
    return RequestHandler()


@pytest.mark.asyncio
async def test_validate_params(handler):
    params = {'param1': 'value1', 'param2': None, 'param3': 'value3'}
    expected = {'param1': 'value1', 'param3': 'value3'}
    assert handler.validate_params(params) == expected


@pytest.mark.asyncio
async def test_validate_url(handler):
    valid_url = 'http://example.com'
    invalid_url = 'ftp://example.com'
    handler.validate_url(valid_url)
    with pytest.raises(ValueError):
        handler.validate_url(invalid_url)


@pytest.mark.asyncio
async def test_validate_response_success(handler):
    response = AsyncMock(httpx.Response)
    response.status_code = 200
    response.headers = {'Content-Type': 'application/json'}
    response.raise_for_status = AsyncMock()
    handler.validate_response(response)
    response.raise_for_status.assert_called_once()


@pytest.mark.asyncio
async def test_validate_response_failure(handler):
    response = AsyncMock(httpx.Response)
    response.status_code = 500
    response.headers = {'Content-Type': 'application/json'}
    def raise_error():
        raise httpx.HTTPStatusError("Error", request=AsyncMock(), response=response)
    response.raise_for_status = raise_error
    with pytest.raises(httpx.HTTPStatusError):
        handler.validate_response(response)


@pytest.mark.asyncio
async def test_send_request_get_success(handler):
    request_url = 'http://example.com'
    params = {'param1': 'value1'}
    method = 'GET'
    response_json = {'key': 'value'}

    response = AsyncMock(httpx.Response)
    response.status_code = 200
    response.json = AsyncMock(return_value=response_json)
    response.headers = {'Content-Type': 'application/json'}
    response.raise_for_status = AsyncMock()

    with patch('httpx.AsyncClient.request', return_value=response) as mock_request:
        result = await handler.send_request(request_url, params, method)
        assert result == response_json
        mock_request.assert_called_once_with(method, request_url, params=params, json=None, headers=None)


@pytest.mark.asyncio
async def test_send_request_post_success(handler):
    request_url = 'http://example.com'
    params = {'param1': 'value1'}
    method = 'POST'
    response_json = {'key': 'value'}

    response = AsyncMock(httpx.Response)
    response.status_code = 200
    response.json = AsyncMock(return_value=response_json)
    response.headers = {'Content-Type': 'application/json'}
    response.raise_for_status = AsyncMock()

    with patch('httpx.AsyncClient.request', return_value=response) as mock_request:
        result = await handler.send_request(request_url, params, method)
        assert result == response_json
        mock_request.assert_called_once_with(method, request_url, params=None, json=params, headers=None)


@pytest.mark.asyncio
async def test_send_request_failure(handler):
    request_url = 'http://example.com'
    params = {'param1': 'value1'}
    method = 'GET'

    with patch('httpx.AsyncClient.request', side_effect=RequestError("Request failed")):
        with pytest.raises(RequestError):
            await handler.send_request(request_url, params, method)


@pytest.mark.asyncio
async def test_mask_sensitive_data(handler):
    params = {'param1': 'value1', 'token': 'sensitive_token', 'password': 'secret_password'}
    masked_params = handler.mask_sensitive_data(params)
    assert masked_params['param1'] == 'value1'
    assert masked_params['token'] == '****'
    assert masked_params['password'] == '****'


@pytest.mark.asyncio
async def test_request_with_masking(handler):
    request_url = 'http://example.com'
    params = {'param1': 'value1', 'token': 'sensitive_token'}
    method = 'GET'
    response_json = {'key': 'value'}

    response = AsyncMock(httpx.Response)
    response.status_code = 200
    response.json = AsyncMock(return_value=response_json)
    response.headers = {'Content-Type': 'application/json'}
    response.raise_for_status = AsyncMock()

    with patch('httpx.AsyncClient.request', return_value=response) as mock_request:
        result = await handler.request_with_masking(request_url, params, method)
        assert result == response_json
        mock_request.assert_called_once_with(method, request_url, params=params, json=None, headers=None)
