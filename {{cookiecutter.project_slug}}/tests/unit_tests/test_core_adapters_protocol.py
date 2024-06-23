import pytest
from core.adapters.llms.protocol import Config, BaseMessage, SimpleMessage, ChainedMessage, Messenger


def test_base_message_creation():
    data = {
        "msg_type": "job",
        "msg_channel": "test_channel",
        "to_type": "service",
        "data": {}
    }
    message = BaseMessage(**data)
    assert message.msg_id is not None
    assert message.sent_epoch is not None
    assert message.from_instance_id == Config.INSTANCE_ID
    assert message.msg_type == data["msg_type"]


def test_base_message_validation():
    data = {
        "msg_type": "invalid_type",
        "msg_channel": "test_channel",
        "to_type": "service",
        "data": {}
    }
    with pytest.raises(ValueError):
        BaseMessage(**data)


def test_simple_message_creation():
    data = {
        "msg_id": "123",
        "msg_type": "job",
        "msg_channel": "test_channel",
        "from_instance_id": "test_instance",
        "sent_epoch": 123456789
    }
    message = SimpleMessage(**data)
    assert message.msg_id == data["msg_id"]
    assert message.sent_epoch == data["sent_epoch"]


def test_chained_message_add_to_chain():
    base_data = {
        "msg_type": "job",
        "msg_channel": "test_channel",
        "to_type": "service",
        "data": {}
    }
    chained_message = ChainedMessage(**base_data)
    simple_message_data = {
        "msg_id": "123",
        "msg_type": "job",
        "msg_channel": "test_channel",
        "from_instance_id": "test_instance",
        "sent_epoch": 123456789
    }
    simple_message = SimpleMessage(**simple_message_data)
    chained_message.add_to_chain(simple_message)
    assert len(chained_message.msg_chain) == 1
    assert chained_message.msg_chain[0].msg_id == simple_message.msg_id


@pytest.fixture
def base_message_data():
    return {
        "msg_type": "job",
        "msg_channel": "test_channel",
        "data": {"example": "data"}
    }


def test_messenger_to_message_json_without_prev_msg(base_message_data):
    json_message = Messenger.to_message_json(**base_message_data)
    assert json_message is not None
    assert isinstance(json_message, str)
    message = ChainedMessage.parse_raw(json_message)
    assert message.msg_type == base_message_data["msg_type"]
    assert message.data == base_message_data["data"]
    assert len(message.msg_chain) == 0  # No previous message, so msg_chain should be empty


def test_messenger_to_message_json_with_prev_msg(base_message_data):
    # First message without a previous message
    first_json_message = Messenger.to_message_json(**base_message_data)
    first_message = ChainedMessage.parse_raw(first_json_message)
    # Second message, with the first message as its predecessor
    second_json_message = Messenger.to_message_json(prev_msg=first_message, **base_message_data)
    second_message = ChainedMessage.parse_raw(second_json_message)
    assert second_message.msg_type == base_message_data["msg_type"]
    assert second_message.data == base_message_data["data"]
    # Now, msg_chain should contain one message
    assert len(second_message.msg_chain) == 1
    assert second_message.msg_chain[0].msg_id == first_message.msg_id  # The ID should match the first message's ID


def test_messenger_from_message_json(base_message_data):
    json_message = Messenger.to_message_json(**base_message_data)
    recovered_message = Messenger.from_message_json(json_message)
    assert isinstance(recovered_message, ChainedMessage)
    assert recovered_message.msg_type == base_message_data["msg_type"]
    assert recovered_message.data == base_message_data["data"]
