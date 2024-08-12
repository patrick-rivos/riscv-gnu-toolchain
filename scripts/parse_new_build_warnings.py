from typing import Dict, Set
from pathlib import Path
import re
import argparse

PRE_COMMIT = "pre-commit"
POST_COMMIT = "post-commit"


class WarningParser:
    def __init__(self):
        self.message = ""

    def parse(self, line: str) -> str:
        """Parse the line and return a warning string if the current line is a start of a new warning
        output:
            "": No new warnings
            string value: parsed warning
        """
        WARNING_PATTERN = re.compile(r".*(:[\w]+)*:\s*warning:.*", re.IGNORECASE)
        FILE_PATTERN = re.compile(r"\s+(?:\d+|\s)\s*\|\s*.*")
        NOTE_PATTERN = re.compile(r".*:\d+(:\d+)?:\s*note:.*", re.IGNORECASE)
        ABSOLUTE_PATH_PATTERN = re.compile(r"(/\S*/)*riscv-gnu-toolchain")
        # Replace all absolute path to path relative to riscv-gnu-toolchain
        # Identical errors could be treated "different" due to the difference in the path
        line = ABSOLUTE_PATH_PATTERN.sub("riscv-gnu-toolchain", line)
        # If we see a warning pattern, always flush the message for a new warning message
        if WARNING_PATTERN.search(line):
            temp, self.message = self.message, line
            return temp
        if self.message:
            # Add File and note lines only if a new warning is being constructed
            if FILE_PATTERN.search(line) or NOTE_PATTERN.search(line):
                self.message += line
                return ""
            # if we hit a random pattern, flush the existing warning message
            temp, self.message = self.message, ""
            return temp
        return ""

    # flush what's left as the last warning message
    def flush(self) -> str:
        temp, self.message = self.message, ""
        return temp


def parse_new_build_warnings(old_build_path: str, new_build_path: str) -> Set[str]:
    """Construct a set of new warnings that are not present in the old build warning"""
    new_build_warnings = construct_warning_set(new_build_path)
    new_warnings = remove_duplicate_warnings(new_build_warnings, old_build_path)
    return new_warnings


# TODO: Combine ConstructWarningSet and RemoveDuplicateWarnings and apply observer pattern
def construct_warning_set(build_path: str) -> Set[str]:
    """Iterate through each warning from the build file and construct a set"""
    path = Path(build_path)
    # validate the path
    if not path.exists:
        raise ValueError(f"{build_path} doesn't exist")
    build_warnings = set()

    def AddToSet(msg: str):
        if msg != "":
            build_warnings.add(msg)

    parser = WarningParser()
    with open(build_path, "r") as file:
        for line in file:
            parsed = parser.parse(line)
            # if the following line is a start of the new warning, parser emits the parsed warning message
            AddToSet(parsed)
    # If new warning line is not given, the last message cannot be flushed automatically
    parsed = parser.flush()
    AddToSet(parsed)
    return build_warnings


def remove_duplicate_warnings(
    new_build_warnings: Set[str], old_build_path: str
) -> Set[str]:
    """Iterate through each warning from the old build file and remove them from the set"""
    path = Path(old_build_path)
    # validate the path
    if not path.exists:
        raise ValueError(f"{old_build_path} doesn't exist")
    if len(new_build_warnings) == 0:
        return new_build_warnings

    def RemoveFromSet(msg: str):
        if msg != "":
            new_build_warnings.discard(msg)

    parser = WarningParser()
    with open(old_build_path, "r") as file:
        for line in file:
            parsed = parser.parse(line)
            # if the following line is a start of the new warning, parser emits the parsed warning message
            RemoveFromSet(parsed)
    # If new warning line is not given, the last message cannot be flushed automatically
    parsed = parser.flush()
    RemoveFromSet(parsed)
    return new_build_warnings


def parse_target(file_name: str) -> str:
    """Parse only the target info from the post commit build log formatted file name.
    Convert mode-arch-abi-hash-multilib-build-log-stderr.log into mode-arch-abi-multilib
    """
    parts = file_name.split("-")
    HASH_INDEX = 3
    # Remove hash and build-log-stderr.log
    del parts[HASH_INDEX]
    BUILD_LOG_INDEX = -3
    return "-".join(parts[:BUILD_LOG_INDEX])


def convert_pre_to_post_format(file_name: str):
    """Convert pre-commit's build log file format to post-commit's format
    pre-commit's build log format: ${patch_number}-{}
    """
    parts = file_name.split("-")
    PATCH_NUMBER_INDEX = 0
    HASH_INDEX = 3
    patch_name = parts.pop(PATCH_NUMBER_INDEX)
    parts.insert(HASH_INDEX, patch_name)
    return "-".join(parts)


def parse_new_build_warnings_from_directory(
    old_build_directory: str, new_build_directory: str, repo: str
) -> Dict[str, Set[str]]:
    """Iterate through new build logs in the new_build_directory to compare with the old build logs from old_build_directory
    After constructing a set of new warnings for each build log, the set of new warnings is printed out to the output file
    """
    # input validation
    old_build_path = Path(old_build_directory)
    if not old_build_path.exists():
        raise ValueError(f"{old_build_directory} doesn't exist")
    new_build_path = Path(new_build_directory)
    if not new_build_path.exists():
        raise ValueError(f"{new_build_directory} doesn't exist")

    new_build_counterpart = dict()
    # Construct the new build counterpart while unrolling the old_build_path.iterdir(). Then searching for the counterpart is not required.
    for file in old_build_path.iterdir():
        hashless = parse_target(file.name)
        new_build_counterpart[hashless] = file

    new_warnings = dict()
    for new_build_file in new_build_path.iterdir():
        # Pre-commit build log files have a different format from post-commit build log files
        new_build_file_name = new_build_file.name
        if repo == PRE_COMMIT:
            new_build_file_name = convert_pre_to_post_format(new_build_file_name)
        hashless = parse_target(new_build_file_name)
        old_build_file = new_build_counterpart[hashless]
        if old_build_file == "":
            raise RuntimeError(f"Older build for {new_build_file} doesn't exist")
        new_warnings[hashless] = parse_new_build_warnings(
            old_build_file, new_build_file
        )
    return new_warnings


def export_build_warnings(warnings_dict: Dict[str, Set[str]], output: str):
    with open(output, "w") as f:
        f.write(
            f"# New build warnings\nA List of all additional build warnings present at this hash\n"
        )
        for target, warnings in sorted(warnings_dict.items(), key=lambda item: item[0]):
            if not warnings:
                continue
            f.write(f"## {target}\n```\n")
            for warning in warnings:
                f.write(warning)
            f.write("```\n---\n")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Download valid log artifacts")
    parser.add_argument(
        "--old-dir",
        required=True,
        type=str,
        help="Directory that only consists of old build's stderr.logs",
    )
    parser.add_argument(
        "--new-dir",
        required=True,
        type=str,
        help="Directory that only consists of new build's stderr.logs",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=str,
        help="Path to the output file that will store all warnings",
    )
    parser.add_argument(
        "--repo",
        required=True,
        choices=[PRE_COMMIT, POST_COMMIT],
        type=str,
        help="Repo that is running the script. It affects the build log file name format",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    new_warnings = parse_new_build_warnings_from_directory(
        args.old_dir, args.new_dir, args.repo
    )
    export_build_warnings(new_warnings, args.output)


if __name__ == "__main__":
    main()
