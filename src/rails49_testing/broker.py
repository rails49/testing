"""A real `mosquitto` on a port of its own, and the `broker` fixture.

Load the fixture with `pytest_plugins = ["rails49_testing.broker"]` in a
`conftest.py`.

Where no `mosquitto` is installed the `broker` fixture skips, so a machine
without one still runs everything else. Under CI it fails instead, so a failed
install reddens the gate rather than removing every test built on the broker.
`CI` in the environment tells the two apart. A `mosquitto` that is installed
but will not start is an error everywhere.
"""

import os
import shutil
import signal
import socket
import subprocess
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import IO, NoReturn

import pytest

from rails49_testing.ports import free_port

SYSTEM_PATHS = "/usr/sbin:/usr/local/sbin"
"""Where packages put `mosquitto`, off many users' `PATH`."""


def mosquitto() -> str | None:
    """The `mosquitto` binary, on `PATH` or in `SYSTEM_PATHS`."""
    return shutil.which(
        "mosquitto", path=f"{os.environ.get('PATH', '')}:{SYSTEM_PATHS}"
    )


def listening(port: int) -> bool:
    """Whether something accepts a connection on this loopback port."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except OSError:
        return False


def until(predicate: Callable[[], bool], timeout: float = 5.0) -> bool:
    """Whether `predicate` came true within `timeout` seconds."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


class Broker:
    """A `mosquitto` on a port of its own, stoppable and startable again on
    the same one: what a broker going away and coming back looks like from a
    client's side.

    Started with only `-p`: it listens on loopback, allows anonymous clients
    and keeps no persistence, so it keeps nothing across a restart. It writes
    to `mosquitto.log` in `folder`. `binary` defaults to `mosquitto()`.
    """

    def __init__(self, folder: Path, binary: str | None = None) -> None:
        self.binary = binary or mosquitto() or "mosquitto"
        self.port = free_port()
        self.log = folder / "mosquitto.log"
        self.process: subprocess.Popen[bytes] | None = None
        self._log_file: IO[bytes] | None = None

    def start(self, timeout: float = 10.0) -> None:
        """Start it and return once it is listening. Raises `RuntimeError`
        with the log if it exits or is not listening within `timeout`."""
        self._log_file = self.log.open("ab")
        self.process = process = subprocess.Popen(
            [self.binary, "-p", str(self.port)],
            stdout=self._log_file,
            stderr=self._log_file,
        )
        deadline = time.monotonic() + timeout
        while not listening(self.port):
            code = process.poll()
            if code is not None or time.monotonic() > deadline:
                raise RuntimeError(
                    f"{self.binary} is not listening on {self.port}, "
                    f"exit code {code}:\n{self.log.read_text()}"
                )
            time.sleep(0.01)

    def stall(self) -> None:
        """Stop the process without closing anything: what is sent to it is
        neither read nor acknowledged, and a connection to it still looks
        up."""
        assert self.process is not None
        self.process.send_signal(signal.SIGSTOP)

    def kill(self) -> None:
        """End it at once, stalled or not."""
        if self.process is not None:
            self.process.kill()
        self.stop()

    def stop(self) -> None:
        """End it, stalled or not, and close its log."""
        if self.process is not None:
            self.process.send_signal(signal.SIGCONT)  # A stalled one takes no SIGTERM.
            self.process.terminate()
            self.process.wait(10)
            self.process = None
        if self._log_file is not None:
            self._log_file.close()
            self._log_file = None


def no_broker(reason: str) -> NoReturn:
    """End the test for want of a broker: a skip on a developer's machine, a
    failure under CI."""
    if os.environ.get("CI", "").lower() in ("", "0", "false"):
        pytest.skip(reason)
    pytest.fail(reason)


@pytest.fixture
def broker(tmp_path: Path) -> Iterator[Broker]:
    """A started `Broker`, stopped when the test ends."""
    binary = mosquitto()
    if binary is None:
        no_broker("no mosquitto installed")
    running = Broker(tmp_path, binary)
    try:
        running.start()
        yield running
    finally:
        running.stop()
