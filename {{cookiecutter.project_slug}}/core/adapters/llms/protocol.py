"""

Messaging Protocol

Used for communicating between workers via redis, postgres, and chromadb

Use pydantic to pack and unpack messages for Redis, Postgres, and Worker Services.

Example:
    message = MyMessage(field1="value1", field2=2)
    message_json = message.json()
    received_message = MyMessage.parse_raw(message_json)

"""
import copy
import time
from datetime import datetime
from uuid import uuid4
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from pydantic.json import pydantic_encoder
from config import Config


def custom_json_encoder(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    # Let the default Pydantic encoder handle all other types
    return pydantic_encoder(obj)


def get_current_time_ns():
    return time.time_ns()


class BaseMessage(BaseModel):
    """
    Base class for messages in the Redis messaging system.

    Attributes:
        msg_id (str): Unique identifier for the message, generated automatically.
        msg_type (str): Type of the message, influencing how Redis handles it.
        msg_channel (str): Redis channel for the message broker service.
        from_instance_id (Optional[str]): ID of the sending instance, defaults to config.
        from_instance_type (Optional[str]): Type of the sending instance, from config.
        from_version (Optional[str]): Version of the sending instance, from config.
        to_id (Optional[str]): ID of the intended recipient. None means broadcast.
        to_type (str): Type of the intended recipient.
        sent_epoch (float): Timestamp of when the message was sent.
        data (dict): The payload of the message.
    """
    # Data about this message
    msg_id: str = Field(default_factory=lambda: str(uuid4()))
    msg_type: str  # How should Redis handle this message? ['job', 'publish', 'cache']
    msg_channel: str  # Redis channel for the message broker service
    # Data about the sender
    from_instance_id: Optional[str] = Config.INSTANCE_ID
    from_instance_type: Optional[str] = Config.INSTANCE_TYPE
    from_version: Optional[str] = Config.VERSION
    to_id: Optional[str] = None
    sent_epoch: float = Field(default_factory=get_current_time_ns)
    # Message payload
    data: dict

    @field_validator('msg_type')
    def check_msg_type(cls, v):
        if v not in ['job', 'publish', 'cache', 'clipboard']:
            raise ValueError("msg_type must be 'job', 'publish', or 'cache'")
        return v


class SimpleMessage(BaseModel):
    """
    Simplified message used for message history
    """
    msg_id: str
    msg_type: str
    msg_channel: str
    from_instance_id: Optional[str] = None
    from_instance_type: Optional[str] = None
    from_version: Optional[str] = None
    sent_epoch: float


class ChainedMessage(BaseMessage):
    """
    Message that includes information about its lineage.

    Attributes:
        msg_chain (List[SimpleMessage]): List of messages leading to this one.
    """
    msg_chain: List[SimpleMessage] = Field(default_factory=list)

    def add_to_chain(self, message: SimpleMessage):
        self.msg_chain.append(message)

    def convert_and_add_to_chain(self, chained_msg: 'ChainedMessage'):
        # Convert the incoming ChainedMessage to a SimpleMessage
        simple_msg = SimpleMessage(
            msg_id=str(chained_msg.msg_id),
            msg_type=chained_msg.msg_type,
            msg_channel=chained_msg.msg_channel,
            from_instance_id=chained_msg.from_instance_id,
            from_instance_type=chained_msg.from_instance_type,
            from_version=chained_msg.from_version,
            sent_epoch=chained_msg.sent_epoch
        )
        # Add the converted SimpleMessage to the current message's chain
        self.add_to_chain(simple_msg)


class Messenger:
    """
    Manages all messages for an app / instance
    """

    @staticmethod
    def to_message_json(msg_type: str, msg_channel: str, data: dict, prev_msg: Optional[ChainedMessage] = None):
        # Recover the msg_chain from the prev message
        msg_chain = []
        if prev_msg and isinstance(prev_msg, ChainedMessage):
            msg_chain = copy.deepcopy(prev_msg.msg_chain)
        # Build the new message
        msg = ChainedMessage(
            msg_type=msg_type,
            msg_channel=msg_channel,
            data=data,
            msg_chain=msg_chain  # Pass the correct msg_chain here
        )
        # Save the most recent message to the chain if applicable
        if prev_msg and isinstance(prev_msg, ChainedMessage):
            msg.convert_and_add_to_chain(prev_msg)
        return msg.json()

    @staticmethod
    def from_message_json(message_json):
        # Ensure correct deserialization from JSON string to ChainedMessage
        return ChainedMessage.parse_raw(message_json)
