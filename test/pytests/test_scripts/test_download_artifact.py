from pathlib import Path
from tempfile import TemporaryDirectory
import sys

scripts_path = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.append(str(scripts_path))
from download_artifact import extract_artifact

# Test Zipfile with a single file
def test_extract_artifact_1():
    fixture_file = Path(__file__).parent.parent / "fixtures" / "test1.zip"
    with TemporaryDirectory() as tmp:
        extract_artifact(str(fixture_file), tmp)
        extracted_files = [file for file in Path(tmp).iterdir()]
        assert(len(extracted_files) == 1)
        assert(Path(extracted_files[0]).name == "test.log")

# Test Zipfile with Nested Directory
def test_extract_artifact_2():
    fixture_file = Path(__file__).parent.parent / "fixtures" / "test2.zip"
    with TemporaryDirectory() as tmp:
        extract_artifact(str(fixture_file), tmp)
        extracted_files = [file for file in Path(tmp).iterdir()]
        assert(len(extracted_files) == 1)
        assert(Path(extracted_files[0]).name == "test.log")

# Test Zipfile with Nested Zipfile
def test_extract_artifact_3():
    fixture_file = Path(__file__).parent.parent / "fixtures" / "test3.zip"
    with TemporaryDirectory() as tmp:
        extract_artifact(str(fixture_file), tmp)
        extracted_files = [file for file in Path(tmp).iterdir()]
        assert(len(extracted_files) == 1)
        assert(Path(extracted_files[0]).name == "test1.zip")
