"""The port a test's server listens on, picked so nothing else can take it.

The caller is told the number before anything binds it, so a number picked by
binding `:0` and closing the socket would be a number nobody holds: the kernel
is free to hand it to the next outbound connection, which it draws from that
same ephemeral range.

So the numbers come from below that range, where no outbound socket is given
one, and from a cursor that offers each of them once, so no two callers in a
run are given the same. Each is offered to the kernel first, so a number a
program outside the run is listening on is stepped over.
"""

import os
import random
import socket
from pathlib import Path

LOCAL_RANGE = Path("/proc/sys/net/ipv4/ip_local_port_range")
"""Where Linux says which numbers it hands out by itself. A Mac says it
through `sysctl` and keeps IANA's, which is the fallback below."""

BAND = 4096
"""How many numbers a run may be given, counting down from the ephemeral
range. Wide enough that no suite exhausts it and narrow enough to stay clear
of the registered ports a developer's machine is serving."""


def ephemeral_first() -> int:
    """The bottom of the range the kernel draws outbound connections from."""
    try:
        first, _last = LOCAL_RANGE.read_text().split()
    except OSError:
        return 49152  # IANA's, and what a Mac uses
    return int(first)


EPHEMERAL_FIRST = ephemeral_first()


def bindable(port: int) -> bool:
    """Whether the kernel will give this number to a server asking for it.
    Loopback, because that is where everything a suite starts listens."""
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


class Ports:
    """The numbers one run hands out: a cursor over a band of them, walking
    from a random start so two runs on one machine are unlikely to collide.
    `free_port` uses the one instance below.
    """

    def __init__(self, first: int, last: int, start: int | None = None) -> None:
        self._first = first
        self._last = last
        self._next = random.randint(first, last) if start is None else start
        self._given: set[int] = set()

    def take(self) -> int:
        for _ in range(self._last - self._first + 1):
            port = self._next
            self._next = self._first if port >= self._last else port + 1
            if port in self._given or not bindable(port):
                continue
            self._given.add(port)
            return port
        raise RuntimeError(f"no free port between {self._first} and {self._last}")


def share(first: int, last: int, worker: str | None, workers: int) -> tuple[int, int]:
    """This process's part of the band: all of it in a run of its own, and
    under pytest-xdist the worker's own slice. Each worker is a process with
    a cursor of its own, so two walking one band could pick the same number
    before either binds it.

    `worker` is xdist's name for it, `gw0` to `gw<workers - 1>`."""
    if worker is None:
        return first, last
    size = (last - first + 1) // workers
    start = first + int(worker.removeprefix("gw")) * size
    return start, start + size - 1


_ports = Ports(
    *share(
        max(1024, EPHEMERAL_FIRST - BAND),
        EPHEMERAL_FIRST - 1,
        os.environ.get("PYTEST_XDIST_WORKER"),
        int(os.environ.get("PYTEST_XDIST_WORKER_COUNT", "1")),
    )
)


def free_port() -> int:
    """A port this run has not given out and nothing is listening on."""
    return _ports.take()
