import json
import time
import logging
import asyncio
import zlib
import pandas as pd
import redis
import redis.asyncio as aioredis
from typing import Dict, Union
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedisAdapter:
    """
    Redis Adapter - Caching, Vector Caching, Comms, Pub-Sub at high speed in memory
    """

    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, password: str = None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.r = redis.Redis(
            host=self.host, port=self.port, db=self.db, password=self.password, decode_responses=True
        )
        self.pubsub = None

    async def async_init(self):
        self.async_r = aioredis.from_url(
            f"redis://{self.host}:{self.port}/{self.db}", password=self.password
        )

    @classmethod
    def serialize_message(cls, message: Union[pd.DataFrame, Dict, list]) -> str:
        try:
            if isinstance(message, pd.DataFrame):
                return message.to_json(orient='records')
            elif isinstance(message, (dict, list)):
                return json.dumps(message)
            else:
                raise TypeError(f'unknown serialization type: {type(message)}')
        except Exception as e:
            logger.error(f'Error serializing message: {e}')
            raise

    @classmethod
    def deserialize_message(cls, message: str, as_df: bool = False) -> Union[pd.DataFrame, dict, list]:
        try:
            if as_df:
                return pd.read_json(message, orient='records')
            else:
                return json.loads(message)
        except Exception as e:
            logger.error(f'Error deserializing message: {e}')
            raise

    def subscribe(self, topic: str):
        try:
            self.pubsub = self.r.pubsub()
            self.pubsub.subscribe(topic)
        except Exception as e:
            logger.error(f'Error subscribing to topic {topic}: {e}')
            raise

    def unsubscribe(self, topic: str):
        try:
            if self.pubsub:
                self.pubsub.unsubscribe(topic)
                time.sleep(0.05)
        except Exception as e:
            logger.error(f'Error unsubscribing from topic {topic}: {e}')
            raise

    def publish(self, topic: str, message: Union[str, int, float, dict, list, pd.DataFrame]):
        try:
            if not isinstance(message, (str, int, float)):
                message = RedisAdapter.serialize_message(message)
            self.r.publish(topic, message)
        except Exception as e:
            logger.error(f'Error publishing message to topic {topic}: {e}')
            raise

    def enqueue_job(self, queue_name: str, job_data: dict):
        """
        Enqueue a job to the specified Redis queue.
        Used for scheduling jobs with workers
        """
        try:
            assert 'job_name' in job_data
            self.r.rpush(queue_name, json.dumps(job_data))
        except Exception as e:
            logger.error(f'Error enqueuing job to queue {queue_name}: {e}')
            raise

    def dequeue_job(self, queue_name: str) -> Union[dict, None]:
        """Dequeue a job from the specified Redis queue."""
        try:
            job = self.r.lpop(queue_name)
            if job is not None:
                return json.loads(job)
            return None
        except Exception as e:
            logger.error(f'Error dequeuing job from queue {queue_name}: {e}')
            raise

    def health_check(self) -> bool:
        """Check if Redis server is available."""
        try:
            return self.r.ping()
        except Exception as e:
            logger.error(f'Redis health check failed: {e}')
            return False

    def set_with_expiration(self, key: str, value: Union[str, int, float, dict, list, pd.DataFrame], ex: int):
        """Set a key with an expiration time."""
        try:
            if not isinstance(value, (str, int, float)):
                value = RedisAdapter.serialize_message(value)
            self.r.setex(key, ex, value)
        except Exception as e:
            logger.error(f'Error setting key {key} with expiration: {e}')
            raise

    def publish_with_filter(self, topic: str, message: Union[str, int, float, dict, list, pd.DataFrame], filter_func):
        """Publish a message with a filter function."""
        try:
            if not isinstance(message, (str, int, float)):
                message = RedisAdapter.serialize_message(message)
            if filter_func(message):
                self.r.publish(topic, message)
        except Exception as e:
            logger.error(f'Error publishing message to topic {topic} with filter: {e}')
            raise

    def compress_and_set(self, key: str, value: Union[str, int, float, dict, list, pd.DataFrame], ex: int = None):
        """Set a compressed value with an optional expiration time."""
        try:
            if not isinstance(value, (str, int, float)):
                value = RedisAdapter.serialize_message(value)
            compressed_value = zlib.compress(value.encode('utf-8'))
            if ex:
                self.r.setex(key, ex, compressed_value)
            else:
                self.r.set(key, compressed_value)
        except Exception as e:
            logger.error(f'Error compressing and setting key {key}: {e}')
            raise

    @classmethod
    def decompress_and_get(cls, r: redis.Redis, key: str) -> Union[str, dict, list, pd.DataFrame]:
        """Get and decompress a value."""
        try:
            compressed_value = r.get(key)
            if compressed_value:
                decompressed_value = zlib.decompress(compressed_value).decode('utf-8')
                return cls.deserialize_message(decompressed_value)
            return None
        except Exception as e:
            logger.error(f'Error decompressing and getting key {key}: {e}')
            raise

    async def async_publish(self, topic: str, message: Union[str, int, float, dict, list, pd.DataFrame]):
        """Asynchronously publish a message."""
        try:
            if not isinstance(message, (str, int, float)):
                message = RedisAdapter.serialize_message(message)
            await self.async_r.publish(topic, message)
        except Exception as e:
            logger.error(f'Error asynchronously publishing message to topic {topic}: {e}')
            raise

    async def async_subscribe(self, topic: str):
        """Asynchronously subscribe to a topic."""
        try:
            self.async_pubsub = self.async_r.pubsub()
            await self.async_pubsub.subscribe(topic)
        except Exception as e:
            logger.error(f'Error asynchronously subscribing to topic {topic}: {e}')
            raise

    async def async_unsubscribe(self, topic: str):
        """Asynchronously unsubscribe from a topic."""
        try:
            if self.async_pubsub:
                await self.async_pubsub.unsubscribe(topic)
                await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f'Error asynchronously unsubscribing from topic {topic}: {e}')
            raise

    async def async_enqueue_job(self, queue_name: str, job_data: dict):
        """Asynchronously enqueue a job."""
        try:
            assert 'job_name' in job_data
            await self.async_r.rpush(queue_name, json.dumps(job_data))
        except Exception as e:
            logger.error(f'Error asynchronously enqueuing job to queue {queue_name}: {e}')
            raise

    async def async_dequeue_job(self, queue_name: str) -> Union[dict, None]:
        """Asynchronously dequeue a job."""
        try:
            job = await self.async_r.lpop(queue_name)
            if job is not None:
                return json.loads(job)
            return None
        except Exception as e:
            logger.error(f'Error asynchronously dequeuing job from queue {queue_name}: {e}')
            raise

    def rate_limited(self, calls_per_period: int, period: int):
        """Decorator to rate limit a function."""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                key = f"{func.__name__}:rate_limit"
                current = self.r.get(key)
                if current and int(current) >= calls_per_period:
                    raise Exception("Rate limit exceeded")
                if not current:
                    self.r.set(key, 1, ex=period)
                else:
                    self.r.incr(key)
                return func(*args, **kwargs)

            return wrapper

        return decorator
