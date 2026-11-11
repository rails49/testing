"""An MQTT client that subscribes to every topic and records what it hears."""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from paho.mqtt import client as paho
from paho.mqtt.enums import CallbackAPIVersion


@dataclass(frozen=True)
class Received:
    topic: str
    payload: bytes
    qos: int
    retain: bool
    at: float
    """When it arrived, by `time.monotonic()`."""


class Subscriber:
    """Subscribed to every topic on the loopback broker at `port` once it is
    constructed."""

    def __init__(self, port: int, qos: int = 0) -> None:
        self.messages: list[Received] = []
        subscribed = threading.Event()

        def on_subscribe(*_: object) -> None:
            subscribed.set()

        self.client = paho.Client(CallbackAPIVersion.VERSION2, protocol=paho.MQTTv311)
        self.client.on_message = self._on_message
        self.client.on_subscribe = on_subscribe
        self.client.connect("127.0.0.1", port)
        self.client.subscribe("#", qos)
        self.client.loop_start()
        assert subscribed.wait(5)

    def close(self) -> None:
        self.client.disconnect()
        self.client.loop_stop()

    def on(self, topic: str) -> list[Received]:
        """What has arrived on `topic` so far."""
        return [message for message in list(self.messages) if message.topic == topic]

    def wait_for(
        self, found: Callable[[Received], bool], timeout: float = 5
    ) -> Received:
        """The first message `found` accepts, from those already here or the
        next to come. Raises `AssertionError` after `timeout` seconds."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for message in list(self.messages):
                if found(message):
                    return message
            time.sleep(0.005)
        raise AssertionError(f"not within {timeout} s; have {self.messages[-5:]}")

    def _on_message(
        self, client: paho.Client, userdata: Any, message: paho.MQTTMessage
    ) -> None:
        self.messages.append(
            Received(
                message.topic,
                bytes(message.payload),
                message.qos,
                message.retain,
                time.monotonic(),
            )
        )
