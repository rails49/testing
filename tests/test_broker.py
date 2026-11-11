"""A real mosquitto: started, stalled, killed and started again, and a
subscriber that hears it."""

import time
from pathlib import Path

import pytest
from paho.mqtt import publish

from rails49_testing.broker import Broker, listening
from rails49_testing.subscriber import Subscriber


def send(broker: Broker, topic: str, payload: bytes, retain: bool = False) -> None:
    publish.single(  # pyright: ignore[reportUnknownMemberType]
        topic, payload, retain=retain, hostname="127.0.0.1", port=broker.port
    )


def test_a_broker_that_cannot_start_says_why_at_once(tmp_path: Path) -> None:
    binary = tmp_path / "mosquitto"
    binary.write_text("#!/bin/sh\necho the reason >&2\nexit 3\n")
    binary.chmod(0o755)
    broker = Broker(tmp_path, str(binary))
    started = time.monotonic()
    with pytest.raises(RuntimeError, match="exit code 3:\\nthe reason"):
        broker.start()
    broker.stop()
    assert time.monotonic() - started < 5


def test_a_subscriber_hears_what_is_published(broker: Broker) -> None:
    subscriber = Subscriber(broker.port)
    try:
        send(broker, "a/b", b"hello")
        heard = subscriber.wait_for(lambda message: message.topic == "a/b")
        assert heard.payload == b"hello"
        assert subscriber.on("a/b") == [heard]
    finally:
        subscriber.close()


def test_a_stalled_broker_still_accepts_a_connection(broker: Broker) -> None:
    broker.stall()
    assert listening(broker.port)


def test_a_killed_broker_comes_back_on_its_port_holding_nothing(
    broker: Broker,
) -> None:
    port = broker.port
    send(broker, "kept/until/restart", b"retained", retain=True)
    broker.stall()
    broker.kill()
    assert not listening(port)

    broker.start()
    assert broker.port == port
    subscriber = Subscriber(port)
    try:
        send(broker, "after/restart", b"new")
        subscriber.wait_for(lambda message: message.topic == "after/restart")
        assert subscriber.on("kept/until/restart") == []
    finally:
        subscriber.close()
