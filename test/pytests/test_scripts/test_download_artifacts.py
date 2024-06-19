from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import pytest

scripts_path = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.append(str(scripts_path))
from download_artifacts import download_build_log_artifact
from get_baseline_hash import parse_baseline_hash

@pytest.fixture
@pytest.mark.github_token_required
def base_hash(github_token):
    url = "https://api.github.com/repos/patrick-rivos/gcc-postcommit-ci/issues?state=all&per_page=50"
    base_hash = parse_baseline_hash(url, github_token)
    return base_hash


@pytest.mark.github_token_required
def test_download_build_log_artifact(base_hash, github_token):
    print(f"Base hash: {base_hash}")
    with TemporaryDirectory() as tmp_dir:
        target = "newlib-rv64gc-lp64d"
        template = target + "-{}-non-multilib"
        # find base hash
        download_build_log_artifact(template, base_hash , "patrick-rivos/gcc-postcommit-ci", github_token, tmp_dir)
        build_log_files = [file for file in Path(tmp_dir).iterdir()]
        print(build_log_files)
        BUILD_LOG_FILE_NUM = 1
        assert(len(build_log_files) == BUILD_LOG_FILE_NUM)
        EXPECTED_ZIP_NAME = template.format(base_hash) + "-build-log.zip"
        assert(Path(build_log_files[0]).name == EXPECTED_ZIP_NAME)