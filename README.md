# rails49-testing

Test helpers shared by the rails49 repositories that run a real `mosquitto` in
their tests.

- `rails49_testing.ports`: `free_port()`, a port below the kernel's ephemeral
  range that no other caller in the run has been given. Under pytest-xdist each
  worker takes its own slice.
- `rails49_testing.broker`: `Broker`, a `mosquitto` on a port of its own that
  can be stopped, stalled, killed and started again on the same port; the
  `broker` fixture, a started `Broker`; `listening`, `until` and `no_broker`.
- `rails49_testing.subscriber`: `Subscriber`, a client subscribed to every
  topic that records each `Received` message.

Without `mosquitto` the `broker` fixture skips, except under `CI`, where it
fails. A `mosquitto` that is installed but will not start is an error.

## Use

Add it as a dev dependency from `main`. `uv.lock` pins the commit:

```bash
uv add --dev "rails49-testing @ git+https://github.com/rails49/testing" --branch main
```

Move to a newer commit:

```bash
uv lock --upgrade-package rails49-testing
```

Load the fixture in `conftest.py`:

```python
pytest_plugins = ["rails49_testing.broker"]
```

## What belongs here

Helpers with no domain knowledge. Nothing here names a topic, takes an
`MqttBus` or states a bus promise; that code stays in its repository. If a
change here keeps needing a matching change in a consumer at the same time,
that code belongs in the consumer.

## Development

`scripts/check.sh` is the gate CI runs: Ruff, Black, Pyright and pytest.
