import json
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest

sys.path.append(str(Path(__file__).resolve().parents[3] / "scripts"))
import create_patches_files as discover
import riscv_patch_scope as scope


def diff(path, added="new"):
    return (
        f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n"
        f"@@ -1 +1 @@\n-old\n+{added}\n"
    )


def patch(num, title="Generic cleanup", **extra):
    return {
        "id": num,
        "project": {"id": 6},
        "name": title,
        "diff": diff("gcc/tree.cc"),
        "web_url": f"web/{num}",
        "mbox": f"mbox/{num}",
        "checks": f"checks/{num}",
        "series": [{"id": 111}],
        **extra,
    }


@pytest.mark.parametrize(
    "title",
    [
        "RISC-V: Simplify",
        "[PATCH v2] RISCV: Simplify",
        "riscv64: Simplify",
        "[PATCH,RISC-V,v2] Simplify",
        "[PATCH 2/3] [RISCV] Simplify",
        "GCC/RISC-V: Simplify",
        "RISC-V backend cleanup",
    ],
)
def test_target_subject_does_not_require_a_diff_fetch(title, monkeypatch):
    item = patch(1, title)
    del item["diff"]
    monkeypatch.setattr(
        scope, "patch_detail", lambda _: pytest.fail("unexpected request")
    )
    assert scope.is_gcc_riscv_patch(item)


@pytest.mark.parametrize(
    "title",
    [
        "[PATCH] AArch64: Fix costs as on RISC-V",
        "tests: mention RISC-V in docs",
        "riscv@example.com sent a patch",
        "[PATCH,riscv@example.com] Fix costs",
    ],
)
def test_incidental_subject_reference_does_not_select_patch(title):
    assert not scope.is_gcc_riscv_patch(patch(1, title))


@pytest.mark.parametrize(
    "path",
    [
        "gcc/config/riscv/bitmanip.md",
        "gcc/testsuite/gcc.target/riscv/test.c",
        "gcc/testsuite/g++.target/riscv/test.C",
        "libgcc/config/riscv/foo.S",
        "gcc/common/config/riscv/riscv-common.cc",
    ],
)
def test_list_entry_fetches_target_path_from_patch_detail(path, monkeypatch):
    item = patch(42)
    del item["diff"]
    lookup = Mock(return_value=patch(42, diff=diff(path)))
    monkeypatch.setattr(scope, "patch_detail", lookup)
    assert scope.is_gcc_riscv_patch(item)
    lookup.assert_called_once_with(42)


def test_metadata_and_source_lines_are_not_paths(monkeypatch):
    monkeypatch.setenv("PATCHWORK_FILTER_EMAILS", "riscv@example.org")
    item = patch(
        1,
        "Improve myriscvtool",
        diff=diff("gcc/tree.cc", "+++ b/gcc/config/riscv/target.md"),
        submitter={"email": "riscv@example.org"},
        content="touches RISC-V",
        headers={"To": "riscv@example.org"},
        series=[{"name": "RISC-V"}],
    )
    assert not scope.is_gcc_riscv_patch(item)
    assert not scope.is_gcc_riscv_patch(
        patch(2, diff=diff("gcc/config/riscv-other/test.c"))
    )
    assert not scope.is_gcc_riscv_patch(patch(3, "RISC-V", project={"id": 9}))


def test_rename_out_of_arch_directory_is_a_target_change():
    rename = (
        "diff --git a/gcc/config/riscv/a.c b/gcc/config/a.c\nsimilarity index 100%\n"
        "rename from gcc/config/riscv/a.c\nrename to gcc/config/a.c\n"
    )
    assert scope.is_gcc_riscv_patch(patch(1, diff=rename))


@pytest.mark.parametrize("entry", ["-patch", "-file", "window"])
def test_discovery_entries_emit_only_target_with_ordered_prerequisites(
    entry, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    prereq, target, unrelated = (
        patch(1),
        patch(2, "RV change", diff=diff("gcc/config/riscv/riscv.cc")),
        patch(3),
    )
    # The prereq is outside the polling window and never itself queued.
    series = {
        "name": "Compiler changes",
        "web_url": "series-link",
        "patches": [prereq, target, unrelated],
    }
    monkeypatch.setattr(
        discover, "request_page", lambda *a, **kw: Mock(json=lambda: series)
    )
    monkeypatch.setattr(
        discover, "patch_detail", lambda n: {1: prereq, 2: target, 3: unrelated}[int(n)]
    )
    if entry == "window":
        monkeypatch.setattr(
            discover,
            "window_patches",
            lambda a, b: [target, unrelated] if a == "start" else [],
        )
        argv = ["-start", "start", "-end", "end", "-backup", "prior"]
    elif entry == "-file":
        Path("ids").write_text("2 3")
        argv = ["-file", "ids"]
    else:
        argv = ["-patch", "2"]
    monkeypatch.setattr(sys, "argv", ["create_patches_files.py", *argv])
    discover.main()
    name = "111-Compiler_changes-2"
    assert json.loads(Path("artifact_names.txt").read_text()) == [name]
    assert (Path("patch_urls") / name).read_text().splitlines() == ["mbox/1", "mbox/2"]
    assert (
        (Path("patchworks_metadata") / name)
        .read_text()
        .endswith("Last patch applied: web/2\n2")
    )
    if entry == "-patch":
        monkeypatch.setattr(sys, "argv", ["create_patches_files.py", "-patch", "3"])
        discover.main()
        assert json.loads(Path("artifact_names.txt").read_text()) == []


@pytest.mark.parametrize(
    "args",
    [["-all-patches"], ["--all-patches"], ["--project", "7"], [], ["-start", "s"]],
)
def test_broadening_arguments_rejected(args, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["create_patches_files.py", *args])
    with pytest.raises(SystemExit) as err:
        discover.parse_arguments()
    assert err.value.code == 2
