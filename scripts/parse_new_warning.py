from typing import Dict, Set
from pathlib import Path
import re
import argparse

class WarningParser:
    def __init__(self):
        self.message = ""
    def parse(self,line:str)->str:
        WARNING_PATTERN = re.compile(r'.*(:[\w]+)*:\s*warning:.*', re.IGNORECASE)
        FILE_PATTERN = re.compile(r'\s+(?:\d+|\s)\s*\|\s*.*')
        NOTE_PATTERN = re.compile(r'.*:\d+(:\d+)?:\s*note:.*', re.IGNORECASE)
        ABSOLUTE_PATH_PATTERN = re.compile(r'(/\S*/)*riscv-gnu-toolchain')
        # Replace all absolute path to path relative to riscv-gnu-toolchain
        # Identical errors could be treated "different" due to the difference in the path
        line = ABSOLUTE_PATH_PATTERN.sub('riscv-gnu-toolchain', line)
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
    def flush(self)->str:
        temp, self.message = self.message, ""
        return temp

'''
    Construct a set of new warnings that are not present in the old build warning
'''
def parse_new_warnings(old_build_path: str, new_build_path: str)->Set[str]:
    new_build_warnings = construct_warning_set(new_build_path)
    new_warnings = remove_duplicate_warnings(new_build_warnings, old_build_path)
    return new_warnings

'''
    Iterate through each warning from the build file and construct a set
'''
# TODO: Combine ConstructWarningSet and RemoveDuplicateWarnings and apply observer pattern
def construct_warning_set(build_path: str)-> Set[str]:
    path = Path(build_path)
    # validate the path
    if not path.exists:
        raise ValueError(f"{build_path} doesn't exist")
    build_warnings = set()
    def AddToSet(msg: str):
        if msg != "":
            build_warnings.add(msg)
    parser = WarningParser()
    with open(build_path, 'r') as file:
        for line in file:
            parsed = parser.parse(line)
            # if the following line is a start of the new warning, parser emits the parsed warning message
            AddToSet(parsed)
    # If new warning line is not given, the last message cannot be flushed automatically
    parsed = parser.flush()
    AddToSet(parsed)
    return build_warnings

'''
    Iterate through each warning from the old build file and remove them from the set
'''
def remove_duplicate_warnings(new_build_warnings: Set[str], old_build_path: str)->Set[str]:
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
    with open(old_build_path, 'r') as file:
        for line in file:
            parsed = parser.parse(line)
            # if the following line is a start of the new warning, parser emits the parsed warning message
            RemoveFromSet(parsed)
    # If new warning line is not given, the last message cannot be flushed automatically
    parsed = parser.flush()
    RemoveFromSet(parsed)
    return new_build_warnings

'''
    Export the warnings without extra new line to a given file_path
'''
def export_warnings_to_file(file_path: str, warning_set: Set[str]):
    path = Path(file_path)
    # validate the path
    if not path.exists:
        raise ValueError(f"{file_path} doesn't exist")

    with open(file_path, 'w') as file:
        for warning in warning_set:
            file.write(warning)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Download valid log artifacts")
    parser.add_argument(
        "--old",
        required=True,
        type=str,
        help="Path to old build's stderr.log",
    )
    parser.add_argument(
        "--new",
        required=True,
        type=str,
        help="Path to new build's stderr.log",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=str,
        help="Path to the output file that would store warnings information",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    new_warnings = parse_new_warnings(args.old, args.new)
    export_warnings_to_file(args.output, new_warnings)

if __name__ == '__main__':
    main()
