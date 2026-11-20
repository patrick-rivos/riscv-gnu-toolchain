from pathlib import Path
import sys

import pytest

scripts_path = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.append(str(scripts_path))

from check_patch_checks import check_patch, get_patches, get_patchwork_check_username


def patchwork_check(
    username, context="lint", description="Lint passed", state="success"
):
    return {
        "user": {"username": username},
        "context": context,
        "description": description,
        "state": state,
    }


def install_checks(monkeypatch, checks):
    monkeypatch.setattr("check_patch_checks.make_api_request", lambda url: ({}, checks))


def test_patchwork_check_username_is_required(monkeypatch):
    monkeypatch.delenv("PATCHWORK_CHECK_USERNAME", raising=False)

    with pytest.raises(RuntimeError, match="PATCHWORK_CHECK_USERNAME"):
        get_patchwork_check_username()


def test_patch_discovery_requires_username_even_when_no_patches(monkeypatch):
    def fail_request(_url):
        raise AssertionError("API should not be called")

    monkeypatch.delenv("PATCHWORK_CHECK_USERNAME", raising=False)
    monkeypatch.setattr("check_patch_checks.make_api_request", fail_request)

    with pytest.raises(RuntimeError, match="PATCHWORK_CHECK_USERNAME"):
        get_patches("start", "end")


def test_patch_discovery_accepts_empty_page_without_link(monkeypatch, tmp_path):
    monkeypatch.setenv("PATCHWORK_CHECK_USERNAME", "rise-ci")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("check_patch_checks.make_api_request", lambda _url: ({}, []))

    get_patches("start", "end")

    assert not (tmp_path / "patch_numbers_to_run.txt").exists()


def test_patch_discovery_follows_next_page_until_link_is_absent(monkeypatch, tmp_path):
    monkeypatch.setenv("PATCHWORK_CHECK_USERNAME", "rise-ci")
    monkeypatch.chdir(tmp_path)
    calls = []

    def fake_request(url):
        calls.append(url)
        if len(calls) == 1:
            return {"Link": '<https://patchwork.example/page/2>; rel="next"'}, [
                {"id": 1, "project": {"id": 6}, "name": "RISC-V: change"}
            ]
        return {}, [
            {"id": 2, "project": {"id": 6}, "name": "RISCV: change"},
            {"id": 3, "project": {"id": 6}, "name": "generic", "diff": None},
            {"id": 4, "project": {"id": 7}, "name": "RISC-V"},
        ]

    monkeypatch.setattr("check_patch_checks.make_api_request", fake_request)
    monkeypatch.setattr("check_patch_checks.check_patch", lambda _patch, _user: True)

    get_patches("start", "end")

    assert len(calls) == 2
    assert "page=2" in calls[1]
    assert "q=" not in calls[0]
    assert (tmp_path / "patch_numbers_to_run.txt").read_text() == "1 2"


def test_check_patch_only_counts_configured_username(monkeypatch):
    monkeypatch.setenv("PATCHWORK_CHECK_USERNAME", "rise-ci")
    install_checks(
        monkeypatch,
        [
            patchwork_check("rise-ci"),
            patchwork_check("rise-ci", context="apply-patch"),
            patchwork_check("someone-else", context="toolchain-ci-rise-test"),
        ],
    )

    assert check_patch({"checks": "https://patchwork.example/checks"})


def test_check_patch_reruns_applied_patch_without_testsuite_result(monkeypatch):
    monkeypatch.setenv("PATCHWORK_CHECK_USERNAME", "rise-ci")
    install_checks(
        monkeypatch,
        [
            patchwork_check("rise-ci", description="Lint starting"),
            patchwork_check("rise-ci"),
            patchwork_check(
                "rise-ci", context="apply-patch", description="Patch applied"
            ),
        ],
    )

    assert check_patch({"checks": "https://patchwork.example/checks"})


@pytest.mark.parametrize("final_state", ["success", "fail", "warning"])
def test_check_patch_does_not_rerun_after_testsuite_result(monkeypatch, final_state):
    monkeypatch.setenv("PATCHWORK_CHECK_USERNAME", "rise-ci")
    install_checks(
        monkeypatch,
        [
            patchwork_check("rise-ci", description="Lint starting"),
            patchwork_check("rise-ci"),
            patchwork_check(
                "rise-ci", context="apply-patch", description="Patch applied"
            ),
            patchwork_check(
                "rise-ci",
                context="toolchain-ci-rise-test",
                description="Testing passed",
                state=final_state,
            ),
        ],
    )

    assert not check_patch({"checks": "https://patchwork.example/checks"})


def test_check_patch_reruns_when_testsuite_result_is_pending(monkeypatch):
    monkeypatch.setenv("PATCHWORK_CHECK_USERNAME", "rise-ci")
    install_checks(
        monkeypatch,
        [
            patchwork_check("rise-ci", description="Lint starting", state="pending"),
            patchwork_check("rise-ci"),
            patchwork_check(
                "rise-ci", context="apply-patch", description="Patch applied"
            ),
            patchwork_check(
                "rise-ci",
                context="toolchain-ci-rise-test",
                description="Testing started",
                state="pending",
            ),
        ],
    )

    assert check_patch({"checks": "https://patchwork.example/checks"})


def test_check_patch_does_not_rerun_apply_failure(monkeypatch):
    monkeypatch.setenv("PATCHWORK_CHECK_USERNAME", "rise-ci")
    install_checks(
        monkeypatch,
        [
            patchwork_check("rise-ci", description="Lint starting"),
            patchwork_check("rise-ci"),
            patchwork_check(
                "rise-ci",
                context="apply-patch",
                description="Patch failed to apply",
                state="fail",
            ),
        ],
    )

    assert not check_patch({"checks": "https://patchwork.example/checks"})
