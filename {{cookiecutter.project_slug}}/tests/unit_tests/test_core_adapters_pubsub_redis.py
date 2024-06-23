import pytest
import json
import pandas as pd
import asyncio
import zlib
import aioredis
from unittest.mock import MagicMock, patch
from redis.exceptions import RedisError
from redis import Redis
from core.adapters.pubsub.redis import RedisAdapter


@pytest.fixture
def redis_adapter():
    return RedisAdapter()


def test_serialize_message_dict(redis_adapter):
    message = {"key": "value"}
    serialized = redis_adapter.serialize_message(message)
    assert serialized == json.dumps(message)


def test_serialize_message_dataframe(redis_adapter):
    df = pd.DataFrame([{"key": "value"}])
    serialized = redis_adapter.serialize_message(df)
    assert serialized == df.to_json(orient='records')


def test_deserialize_message_dict(redis_adapter):
    message = '{"key": "value"}'
    deserialized = redis_adapter.deserialize_message(message)
    assert deserialized == json.loads(message)


def test_deserialize_message_dataframe(redis_adapter):
    message = '[{"key": "value"}]'
    deserialized = redis_adapter.deserialize_message(message, as_df=True)
    assert isinstance(deserialized, pd.DataFrame)


@patch.object(Redis, 'publish', return_value=None)
def test_publish(redis_publish_mock, redis_adapter):
    message = {"key": "value"}
    redis_adapter.publish('test_topic', message)
    redis_publish_mock.assert_called_once_with('test_topic', json.dumps(message))


@patch.object(Redis, 'rpush', return_value=None)
def test_enqueue_job(redis_rpush_mock, redis_adapter):
    job_data = {"job_name": "test_job"}
    redis_adapter.enqueue_job('test_queue', job_data)
    redis_rpush_mock.assert_called_once_with('test_queue', json.dumps(job_data))


@patch.object(Redis, 'lpop', return_value=json.dumps({"job_name": "test_job"}))
def test_dequeue_job(redis_lpop_mock, redis_adapter):
    job = redis_adapter.dequeue_job('test_queue')
    assert job == {"job_name": "test_job"}
    redis_lpop_mock.assert_called_once_with('test_queue')


@patch.object(Redis, 'ping', return_value=True)
def test_health_check(redis_ping_mock, redis_adapter):
    assert redis_adapter.health_check() is True
    redis_ping_mock.assert_called_once_with()


@patch.object(Redis, 'setex', return_value=True)
def test_set_with_expiration(redis_setex_mock, redis_adapter):
    redis_adapter.set_with_expiration('key', 'value', 10)
    redis_setex_mock.assert_called_once_with('key', 10, 'value')


@patch.object(Redis, 'get', return_value=None)
def test_decompress_and_get(redis_get_mock, redis_adapter):
    assert redis_adapter.decompress_and_get(redis_adapter.r, 'key') is None
    redis_get_mock.assert_called_once_with('key')


@pytest.mark.asyncio
async def test_async_publish():
    adapter = RedisAdapter()
    await adapter.async_init()
    with patch.object(adapter.async_r, 'publish', new_callable=MagicMock) as mock_publish:
        future = asyncio.Future()
        future.set_result(None)
        mock_publish.return_value = future
        await adapter.async_publish('test_topic', 'message')
        mock_publish.assert_called_once_with('test_topic', 'message')


@pytest.mark.asyncio
async def test_async_subscribe():
    adapter = RedisAdapter()
    await adapter.async_init()
    with patch.object(adapter.async_r, 'pubsub', new_callable=MagicMock) as mock_pubsub:
        mock_pubsub_instance = MagicMock()
        future = asyncio.Future()
        future.set_result(None)
        mock_pubsub_instance.subscribe.return_value = future
        mock_pubsub.return_value = mock_pubsub_instance
        await adapter.async_subscribe('test_topic')
        mock_pubsub_instance.subscribe.assert_called_once_with('test_topic')


@pytest.mark.asyncio
async def test_async_enqueue_job():
    adapter = RedisAdapter()
    await adapter.async_init()
    job_data = {"job_name": "test_job"}
    with patch.object(adapter.async_r, 'rpush', new_callable=MagicMock) as mock_rpush:
        future = asyncio.Future()
        future.set_result(None)
        mock_rpush.return_value = future
        await adapter.async_enqueue_job('test_queue', job_data)
        mock_rpush.assert_called_once_with('test_queue', json.dumps(job_data))


@pytest.mark.asyncio
async def test_async_dequeue_job():
    adapter = RedisAdapter()
    await adapter.async_init()
    with patch.object(adapter.async_r, 'lpop', new_callable=MagicMock) as mock_lpop:
        future = asyncio.Future()
        future.set_result(json.dumps({"job_name": "test_job"}))
        mock_lpop.return_value = future
        job = await adapter.async_dequeue_job('test_queue')
        assert job == {"job_name": "test_job"}
        mock_lpop.assert_called_once_with('test_queue')


@patch.object(Redis, 'pubsub', return_value=MagicMock())
def test_subscribe(redis_pubsub_mock, redis_adapter):
    redis_adapter.subscribe('test_topic')
    redis_pubsub_mock.return_value.subscribe.assert_called_once_with('test_topic')


@patch.object(Redis, 'pubsub', return_value=MagicMock())
def test_unsubscribe(redis_pubsub_mock, redis_adapter):
    redis_adapter.subscribe('test_topic')  # First, subscribe to initialize the pubsub
    redis_adapter.unsubscribe('test_topic')
    redis_pubsub_mock.return_value.unsubscribe.assert_called_once_with('test_topic')


@patch.object(Redis, 'publish', return_value=None)
def test_publish_with_filter(redis_publish_mock, redis_adapter):
    message = {"key": "value"}
    filter_func = lambda msg: "key" in json.loads(msg)
    redis_adapter.publish_with_filter('test_topic', message, filter_func)
    redis_publish_mock.assert_called_once_with('test_topic', json.dumps(message))


def test_publish_with_filter_no_publish(redis_adapter):
    with patch.object(redis_adapter.r, 'publish') as redis_publish_mock:
        message = {"key": "value"}
        filter_func = lambda msg: "nokey" in json.loads(msg)
        redis_adapter.publish_with_filter('test_topic', message, filter_func)
        redis_publish_mock.assert_not_called()


@patch.object(Redis, 'setex', return_value=True)
def test_compress_and_set(redis_setex_mock, redis_adapter):
    message = "test_value"
    compressed_value = zlib.compress(message.encode('utf-8'))
    redis_adapter.compress_and_set('test_key', message, 10)
    redis_setex_mock.assert_called_once_with('test_key', 10, compressed_value)


@patch.object(Redis, 'set', return_value=True)
def test_compress_and_set_no_expiration(redis_set_mock, redis_adapter):
    message = "test_value"
    compressed_value = zlib.compress(message.encode('utf-8'))
    redis_adapter.compress_and_set('test_key', message)
    redis_set_mock.assert_called_once_with('test_key', compressed_value)


@patch.object(Redis, 'get', return_value=zlib.compress(json.dumps({"key": "value"}).encode('utf-8')))
def test_decompress_and_get(redis_get_mock, redis_adapter):
    result = redis_adapter.decompress_and_get(redis_adapter.r, 'test_key')
    assert result == {"key": "value"}
    redis_get_mock.assert_called_once_with('test_key')


def test_rate_limited(redis_adapter):
    @redis_adapter.rate_limited(1, 60)
    def limited_function():
        return "called"

    with patch.object(redis_adapter.r, 'get', return_value=None):
        with patch.object(redis_adapter.r, 'set', return_value=True) as redis_set_mock:
            assert limited_function() == "called"
            redis_set_mock.assert_called_once()

    with patch.object(redis_adapter.r, 'get', return_value="1"):
        with pytest.raises(Exception, match="Rate limit exceeded"):
            limited_function()


@patch.object(Redis, 'publish', side_effect=RedisError("Redis error"))
def test_publish_exception(redis_publish_mock, redis_adapter):
    with pytest.raises(RedisError, match="Redis error"):
        redis_adapter.publish('test_topic', 'message')


@patch.object(Redis, 'rpush', side_effect=RedisError("Redis error"))
def test_enqueue_job_exception(redis_rpush_mock, redis_adapter):
    with pytest.raises(RedisError, match="Redis error"):
        redis_adapter.enqueue_job('test_queue', {'job_name': 'test_job'})


@patch.object(Redis, 'lpop', side_effect=RedisError("Redis error"))
def test_dequeue_job_exception(redis_lpop_mock, redis_adapter):
    with pytest.raises(RedisError, match="Redis error"):
        redis_adapter.dequeue_job('test_queue')


@pytest.mark.asyncio
async def test_async_publish_exception():
    adapter = RedisAdapter()
    await adapter.async_init()
    with patch.object(adapter.async_r, 'publish', side_effect=RedisError("Redis error")):
        with pytest.raises(RedisError, match="Redis error"):
            await adapter.async_publish('test_topic', 'message')


@pytest.mark.asyncio
async def test_async_subscribe_exception():
    adapter = RedisAdapter()
    await adapter.async_init()
    with patch.object(adapter.async_r, 'pubsub', side_effect=RedisError("Redis error")):
        with pytest.raises(RedisError, match="Redis error"):
            await adapter.async_subscribe('test_topic')


@pytest.mark.asyncio
async def test_async_enqueue_job_exception():
    adapter = RedisAdapter()
    await adapter.async_init()
    with patch.object(adapter.async_r, 'rpush', side_effect=RedisError("Redis error")):
        with pytest.raises(RedisError, match="Redis error"):
            await adapter.async_enqueue_job('test_queue', {'job_name': 'test_job'})


@pytest.mark.asyncio
async def test_async_dequeue_job_exception():
    adapter = RedisAdapter()
    await adapter.async_init()
    with patch.object(adapter.async_r, 'lpop', side_effect=RedisError("Redis error")):
        with pytest.raises(RedisError, match="Redis error"):
            await adapter.async_dequeue_job('test_queue')
