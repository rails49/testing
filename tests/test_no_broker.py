"""A missing broker skips off CI and fails under it."""

import pytest

from rails49_testing.broker import no_broker


def test_no_broker_skips_off_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CI", raising=False)
    with pytest.raises(BaseException) as raised:
        no_broker("no mosquitto installed")
    assert raised.type is pytest.skip.Exception


@pytest.mark.parametrize("says_ci", ["true", "1", "TRUE"])
def test_no_broker_fails_under_ci(
    monkeypatch: pytest.MonkeyPatch, says_ci: str
) -> None:
    monkeypatch.setenv("CI", says_ci)
    with pytest.raises(BaseException) as raised:
        no_broker("no mosquitto installed")
    assert raised.type is pytest.fail.Exception
    assert "mosquitto" in str(raised.value)


@pytest.mark.parametrize("not_ci", ["", "0", "false"])
def test_an_unset_looking_ci_still_skips(
    monkeypatch: pytest.MonkeyPatch, not_ci: str
) -> None:
    monkeypatch.setenv("CI", not_ci)
    with pytest.raises(BaseException) as raised:
        no_broker("mosquitto would not start")
    assert raised.type is pytest.skip.Exception
