import pytest
import json
import asyncio
from core.adapters.pubsub.redis import RedisAdapter


@pytest.fixture(scope='module')
async def async_redis_adapter():
    adapter = RedisAdapter(host='localhost', port=6379, db=0)
    await adapter.async_init()
    yield adapter
    await adapter.async_r.flushdb()  # Clear the database after tests


@pytest.fixture(scope='module')
def sync_redis_adapter():
    adapter = RedisAdapter(host='localhost', port=6379, db=0)
    yield adapter
    adapter.r.flushdb()  # Clear the database after tests


@pytest.mark.asyncio
async def test_async_publish_and_subscribe(async_redis_adapter):
    topic = 'test_topic'
    message = {"key": "value"}
    future = asyncio.Future()

    async def message_handler(msg):
        if msg['type'] == 'message':
            future.set_result(json.loads(msg['data']))

    async_pubsub = async_redis_adapter.async_r.pubsub()
    await async_pubsub.subscribe(topic)
    async_pubsub.run_in_thread(sleep_time=0.01, callback=message_handler)

    await async_redis_adapter.async_publish(topic, message)
    result = await future

    assert result == message
    await async_pubsub.unsubscribe(topic)


def test_publish_and_subscribe(sync_redis_adapter):
    topic = 'test_topic'
    message = {"key": "value"}
    future = asyncio.get_event_loop().create_future()

    def message_handler(msg):
        if msg['type'] == 'message':
            future.set_result(json.loads(msg['data']))

    sync_redis_adapter.pubsub = sync_redis_adapter.r.pubsub()
    sync_redis_adapter.pubsub.subscribe(**{topic: message_handler})
    sync_redis_adapter.pubsub.run_in_thread(sleep_time=0.01)

    sync_redis_adapter.publish(topic, message)
    result = future.result()

    assert result == message
    sync_redis_adapter.unsubscribe(topic)


@pytest.mark.asyncio
async def test_async_enqueue_and_dequeue_job(async_redis_adapter):
    queue_name = 'test_queue'
    job_data = {"job_name": "test_job"}

    await async_redis_adapter.async_enqueue_job(queue_name, job_data)
    dequeued_job = await async_redis_adapter.async_dequeue_job(queue_name)

    assert dequeued_job == job_data


def test_enqueue_and_dequeue_job(sync_redis_adapter):
    queue_name = 'test_queue'
    job_data = {"job_name": "test_job"}

    sync_redis_adapter.enqueue_job(queue_name, job_data)
    dequeued_job = sync_redis_adapter.dequeue_job(queue_name)

    assert dequeued_job == job_data


@pytest.mark.asyncio
async def test_async_set_and_get_with_expiration(async_redis_adapter):
    key = 'test_key'
    value = 'test_value'
    expiration = 1  # seconds

    await async_redis_adapter.set_with_expiration(key, value, expiration)
    stored_value = await async_redis_adapter.async_r.get(key)

    assert stored_value == value

    await asyncio.sleep(expiration + 0.5)
    stored_value_after_expiration = await async_redis_adapter.async_r.get(key)

    assert stored_value_after_expiration is None


def test_set_and_get_with_expiration(sync_redis_adapter):
    key = 'test_key'
    value = 'test_value'
    expiration = 1  # seconds

    sync_redis_adapter.set_with_expiration(key, value, expiration)
    stored_value = sync_redis_adapter.r.get(key)

    assert stored_value == value

    import time
    time.sleep(expiration + 0.5)
    stored_value_after_expiration = sync_redis_adapter.r.get(key)

    assert stored_value_after_expiration is None
