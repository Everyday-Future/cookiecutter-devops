"""

(DEPRECATED) Broker for MQTT client

Not currently used, but here for backup purposes

"""
# import time
# import uuid
# from datetime import datetime
# import paho.mqtt.client as mqtt
# import threading
# from config import Config
#
#
# class Broker:
#     def __init__(self, broker_address=None, port=None):
#         self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, protocol=mqtt.MQTTv5)
#         self.broker_address = broker_address or Config.MQTT_SERVER
#         self.port = port or Config.MQTT_PORT
#         self.client.on_connect = self.on_connect
#         self.client.on_message = self.on_message
#         # TODO - Store received messages in a deque
#         self.received_messages = []
#
#     def on_connect(self, client, userdata, flags, reason_code, properties):
#         print(f"Connected with result code {reason_code}")
#         # Subscribing in on_connect() means that if we lose the connection and
#         # reconnect then subscriptions will be renewed.
#         client.subscribe("test/topic")
#
#     def on_message(self, client, userdata, msg):
#         print(f"Received message '{msg.payload.decode()}' on topic '{msg.topic}'")
#         # Retain messages in the list
#         self.received_messages.append((msg.topic, msg.payload.decode()))
#
#     def start(self):
#         self.client.connect(self.broker_address, self.port, 60)
#         # Start the client loop in its own thread
#         thread = threading.Thread(target=self.client.loop_forever)
#         thread.daemon = True
#         thread.start()
#
#     def _publish(self, topic, payload, qos=1):
#         self.client.publish(topic, payload, qos)
#
#     def get_received_messages(self):
#         return self.received_messages
#
#     def publish(self, data: dict, topic: str, msg_id: str = None, msg_type: str = 'default', priority: int = 5,
#                 reply_topic: str = None, ack_topic: str = None, meta_history: list = None,
#                 reply_timeout: int = None, ack_timeout: int = None, qos=1):
#         """
#         Publish a message to the PubSub server, decorated with all relevant metadata and history
#
#         reply topic - for async requests and rendezvous operations
#         qos -
#             QoS 0 is appropriate when you need maximum throughput and latency is a concern,
#                 and message loss is acceptable.
#             QoS 1 strikes a balance between reliability and performance, ensuring that messages arrive
#                 at least once without the overhead of QoS 2.
#             QoS 2 should be used for critical messages that require guaranteed delivery without duplication.
#         """
#         if ack_topic is not None:
#             # Go ahead and subscribe to the ack_topic if specifies, as the reply should come quickly
#             pass
#         created_time = time.time()
#         msg = {
#             "metadata": {
#                 "sent_time": created_time,
#                 "sent_datetime": datetime.fromtimestamp(created_time).strftime('%c'),
#                 "msg_id": msg_id or uuid.uuid4(),
#                 "page": 1,
#                 "offset": 0,
#                 "attempt_num": 1,
#                 "sender_id": Config.SERVER_MODE,
#                 "sender_version": Config.VERSION,
#                 "priority": int(priority),
#                 "msg_type": msg_type,
#                 "send_topic": topic,
#                 "reply_topic": reply_topic,   # Optional topic for posting the response. Will wait if specified.
#                 "ack_topic": ack_topic        # Optional topic to acknowledge messages that may take a bit to process
#             },
#             "meta_history": meta_history or [],
#             "data": data
#         }
#         if reply_topic is None:
#             return self._publish(topic=topic, payload=msg, qos=qos)
#         else:
#             # Publish with qos==2 for rendezvous messages
#             self._publish(topic=topic, payload=msg, qos=2)
#             if ack_topic is not None:
#                 # TODO - Wait for message acknowledge or ack_timeout
#                 ack_time = time.time() - created_time
#             # Subscribe to reply topic and wait for the reply message
#             reply_time = time.time() - created_time
#             # Append the meta_history and return the message
#             pass
#
#     def publish_and_wait(self, data: dict, topic: str, msg_id: str, reply_topic: str, ack_topic: str = None,
#                          msg_type: str = 'rendezvous', priority: int = 5, meta_history: list = None, qos=1):
#         """
#         TODO - Rendezvous architecture to drop a message in pubsub, check for ACK, then wait for response
#         """
#         # Publish message
#         # Wait for ACK if
#
#     def subscribe(self, topic, qos: int = 0, **kwargs):
#         return self.client.subscribe(topic=topic, qos=qos, **kwargs)

