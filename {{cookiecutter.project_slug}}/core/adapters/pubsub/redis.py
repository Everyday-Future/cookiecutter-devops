"""

Redis Adapter

Caching, Vector Caching, Comms, Pub-Sub

"""
import json
import time

import pandas as pd
import redis


class RedisAdapter:
    """
    Redis Adapter - Caching, Vector Caching, Comms, Pub-Sub at high speed in memory
    """

    def __init__(self, host='localhost', port=6379, db=0):
        self.r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.pubsub = None

    @classmethod
    def serialize_message(cls, message):
        if isinstance(message, pd.DataFrame):
            message = message.to_json(orient='records')
        elif isinstance(message, (dict, list)):
            message = json.dumps(message)
        else:
            raise TypeError(f'unknown serialization type: {type(message)}')
        return message

    @classmethod
    def deserialize_message(cls, message: str, as_df: bool = False):
        if as_df is True:
            message = pd.read_json(message, orient='records')
        else:
            message = json.loads(message)
        return message

    def subscribe(self, topic):
        pubsub = self.r.pubsub()
        pubsub.subscribe(topic)
        self.pubsub = pubsub
        return pubsub

    def unsubscribe(self, topic):
        if self.pubsub is not None:
            self.pubsub.unsubscribe(topic)
            time.sleep(0.05)

    def publish(self, topic, message):
        if not isinstance(message, (str, int, float)):
            message = RedisAdapter.serialize_message(message)
        self.r.publish(topic, message)

    def enqueue_job(self, queue_name, job_data: dict):
        """
        Enqueue a job to the specified Redis queue.
        Used for scheduling jobs with workers
        """
        assert 'job_name' in job_data
        self.r.rpush(queue_name, json.dumps(job_data))

    def dequeue_job(self, queue_name):
        """Dequeue a job from the specified Redis queue."""
        job = self.r.lpop(queue_name)
        if job is not None:
            return json.loads(job)
        else:
            return None
