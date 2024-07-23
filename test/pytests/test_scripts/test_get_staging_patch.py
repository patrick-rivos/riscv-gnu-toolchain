from pathlib import Path
from tempfile import TemporaryDirectory, NamedTemporaryFile
import re
import pytest
import sys

scripts_path = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.append(str(scripts_path))

from get_staging_patch import parse_run_id_from_body, parse_patch_id_from_body, parse_hash_from_body, parse_hash_from_body

@pytest.fixture
def issue_body()-> str:
    return  '## Precommit CI Run information\nLogs can be found in the associated Github Actions run: https://github.com/ewlu/gcc-precommit-ci/actions/runs/9943458208\n## Patch information\nApplied patches: 1 -> 1\nAssociated series: https://patchwork.sourceware.org/project/gcc/list/?series=35814\nLast patch applied: https://patchwork.sourceware.org/project/gcc/patch/20240703012039.3284024-1-patrick@rivosinc.com/\nPatch id: 93266\n## Build Targets\nSome targets are built as multilibs. If a build target ends with `multilib`, please refer to the table below to see all the targets within that multilib.\n|Target name|`-march` string|\n|-|-|\n|newlib-rv64gc-lp64d-multilib|`rv32gc-ilp32d`, `rv64gc-lp64d`|\n|newlib-rv64gcv-lp64d-multilib|`rv64gcv-lp64d`|\n|linux-rv64gcv-lp64d-multilib|`rv32gcv-ilp32d`, `rv64gcv-lp64d`|\n## Target Information\n|Target Shorthand|`-march` string|\n|-|-|\n|Bitmanip|`gc_zba_zbb_zbc_zbs`|\n## Notes\nTestsuite results use a more lenient allowlist to reduce error reporting with flakey tests. Please take a look at the current [allowlist](https://github.com/ewlu/gcc-precommit-ci/tree/main/test/allowlist).\nResults come from a [sum file comparator](https://github.com/patrick-rivos/riscv-gnu-toolchain/blob/a0a8cabf8ca71bdfbb41e23ab599af9528af772c/scripts/compare_testsuite_log.py). Each patch is applied to a well known, non-broken baseline taken from our\ngcc postcommit framework ([here](https://github.com/patrick-rivos/gcc-postcommit-ci/issues)) which runs the full gcc testsuite every 6 hours.\nIf you have any questions or encounter any issues which may seem like false-positives, please contact us at patchworks-ci@rivosinc.com\n'

@pytest.fixture
def comment_body()->dict:
    return '## Apply Status\n|Target|Status|\n|---|---|\n|Baseline hash: https://github.com/gcc-mirror/gcc/commit/298a576f00c49b8f4529ea2f87b9943a32743250|Applied|\n|Tip of tree hash: https://github.com/gcc-mirror/gcc/commit/398a576f00c49b8f4529ea2f87b9943a32743250|Applied|\n\n## Git log\ngit log --oneline from the most recently applied patch to the baseline\n```\n> git log --oneline 298a576f00c49b8f4529ea2f87b9943a32743250^..HEAD\n298a576f00c i386: Correct AVX10 CPUID emulation\n```\n\n## Notes\nPatch applied successfully\n\n[Additional information](https://github.com/ewlu/gcc-precommit-ci/issues/1911#issue-2409214264)\n'

def test_parse_run_id_from_body(issue_body):
    run_id = parse_run_id_from_body(issue_body)
    assert(run_id == '9943458208')

def test_parse_patch_id_from_body(issue_body):
    patch_id = parse_patch_id_from_body(issue_body)
    assert(patch_id == '93266')

def test_parse_hash_from_body(comment_body):
    baseline = parse_hash_from_body(comment_body, "Baseline hash")
    assert(baseline == '298a576f00c49b8f4529ea2f87b9943a32743250')

def test_parse_hash_from_body(comment_body):
    tip_of_tree = parse_hash_from_body(comment_body, "Tip of tree hash")
    assert(tip_of_tree == '398a576f00c49b8f4529ea2f87b9943a32743250')
