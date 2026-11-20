from pathlib import Path
import sys
from unittest.mock import Mock

import pytest

sys.path.append(str(Path(__file__).resolve().parents[3] / "scripts"))

import create_patches_files as discover


def patch(num):
    return {
        "id": num,
        "name": "RISCV: change",
        "project": {"id": 6},
        "checks": f"checks/{num}",
    }


@pytest.mark.parametrize(
    "username,context,state,include",
    [
        ("another-bot", "toolchain-ci-rise-test", "success", True),
        ("rise-ci", "some-other-check", "success", True),
        ("rise-ci", "toolchain-ci-rise-test", "pending", False),
        ("rise-ci", "toolchain-ci-rise-test", "success", False),
        ("rise-ci", "toolchain-ci-rise-test", "warning", False),
        ("rise-ci", "toolchain-ci-rise-test", "fail", False),
    ],
)
def test_overlap_checks_only_distinct_eligible_candidates(
    monkeypatch, username, context, state, include
):
    monkeypatch.setenv("PATCHWORK_CHECK_USERNAME", "rise-ci")
    get = Mock(
        return_value=Mock(
            json=lambda: [
                {"user": {"username": username}, "context": context, "state": state}
            ]
        )
    )
    monkeypatch.setattr(discover, "request_page", get)
    first, second = patch(1), patch(2)
    result = list(
        discover.selected_patches(
            [first], [first, second, dict(patch(3), project={"id": 9})]
        )
    )
    assert result == ([first, second] if include else [first])
    get.assert_called_once_with("checks/2")


def test_no_username_does_not_drop_shadow_candidate(monkeypatch):
    monkeypatch.delenv("PATCHWORK_CHECK_USERNAME", raising=False)
    assert not discover.has_rise_check(
        [{"user": {"username": "someone"}, "context": "toolchain-ci-rise-test"}]
    )


def test_polling_window_exhausts_pages(monkeypatch):
    first = Mock(json=lambda: [patch(1)], links={"next": {"url": "page2"}})
    last = Mock(json=lambda: [patch(2)], links={})
    get = Mock(side_effect=[first, last])
    monkeypatch.setattr(discover, "request_page", get)
    assert list(discover.window_patches("s", "e")) == [patch(1), patch(2)]
    assert get.call_args_list[0].args[1]["project"] == 6
    assert get.call_args_list[1].args == ("page2", None)
