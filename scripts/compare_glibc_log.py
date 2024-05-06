#!/usr/bin/env python3
from pathlib import Path
import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from collections import Counter


@dataclass
class LibName:
    """Named Tuple for arch abi model"""

    arch: str
    abi: str
    model: str

    def __init__(self, arch: str, abi: str, model: str):
        self.arch = arch.strip().lower()
        self.abi = abi.strip().lower()
        self.model = model.strip().lower()

    def __str__(self):
        return " ".join((self.arch, self.abi, self.model))

    def __hash__(self):
        return hash((self.arch, self.abi, self.model))


@dataclass
class Description:
    """Named Tuple for tool arch abi model"""

    tool: str
    libname: LibName

    def __hash__(self):
        return hash((self.tool, self.libname))


@dataclass
class GlibcFailure:
    """Failure class to group lib's tool failures"""

    fails: List[str] = field(default_factory=list)

    def __str__(self):
        result = ""
        if len(self.fails) > 0:
            result += "### glibc failures\n"
            result += "\n".join(self.fails)
        return result

    def count_failures(
        self
    ) -> Tuple[str, str]:
        """parse (total failures count, unique failures count)"""
        return (str(len(self.fails)), str(len(set(self.fails))))

@dataclass
class ClassifedGlibcFailures:
    """Failures class to distinguish the failure types"""

    resolved: Dict[LibName, GlibcFailure]
    unresolved: Dict[LibName, GlibcFailure]
    new: Dict[LibName, GlibcFailure]

    def failure_dict_to_string(
        self, failure_dict: Dict[LibName, GlibcFailure], failure_name: str
    ):
        result = f"# {failure_name}\n"
        for libname, glibcfailure in failure_dict.items():
            result += f"## {libname}\n"
            result += str(glibcfailure)
        return result

    def __str__(self):
        result = self.failure_dict_to_string(self.resolved, "Resolved Failures")
        result += self.failure_dict_to_string(self.unresolved, "Unresolved Failures")
        result += self.failure_dict_to_string(self.new, "New Failures")
        return result


def parse_arguments():
    parser = argparse.ArgumentParser(description="Testsuite Compare Options")
    parser.add_argument(
        "-plog",
        "--previous-log",
        metavar="<filename>",
        required=True,
        type=str,
        help="Path to the previous testsuite result log",
    )
    parser.add_argument(
        "-phash",
        "--previous-hash",
        metavar="<string>",
        required=True,
        type=str,
        help="Commit hash of the previous GLIBC testsuite log",
    )

    parser.add_argument(
        "-clog",
        "--current-log",
        metavar="<filename>",
        required=True,
        type=str,
        help="Path to the current testsuite result log",
    )

    parser.add_argument(
        "-chash",
        "--current-hash",
        metavar="<string>",
        required=True,
        type=str,
        help="Commit hash of the current GLIBC testsuite log",
    )

    parser.add_argument(
        "-o",
        "--output-markdown",
        default="./testsuite.md",
        metavar="<filename>",
        type=str,
        help="Path to the current testsuite result log",
    )

    parser.add_argument(
        '-ccommitted',
        '--current-hash-committed',
        help="The current hash is an existing GLIBC hash",
        action='store_true'
    )

    return parser.parse_args()


def is_description(line: str) -> bool:
    """checks if the line is a tool description"""
    if line.startswith("\t\t==="):
        return True
    return False


def parse_description(line: str) -> Description:
    """returns 'tool arch abi model'"""
    descriptions = line.split(" ")
    tool = descriptions[1][:-1]
    arch = descriptions[5]
    abi = descriptions[6]
    model = descriptions[7]
    description = Description(tool, LibName(arch, abi, model))
    return description


def parse_failure_name(failure_line: str) -> str:
    failure_components = failure_line.split(" ")
    if len(failure_components) < 2:
        raise ValueError(f"Invalid Failure Log: {failure_line}")
    return failure_components[1]


def parse_testsuite_failures(log_path: str) -> Tuple[Description, List[str]] | None:
    """
    parse testsuite failures from the log in the path
    """
    if not Path(log_path).exists():
        raise ValueError(f"Invalid Path: {log_path}")
    failures: List[str] = []
    with open(log_path, "r") as file:
        description = None
        for line in file:
            if line == "\n":
                break
            if is_description(line):
                new_description = parse_description(line)
                if description is None:
                    description = new_description
                else:
                    assert description == new_description
                failures = []
                continue
            failures.append(line.strip())
    if description is None:
        return None
    else:
        return description, failures


def list_difference(a: List[str], b: List[str]):
    count = Counter(a)
    count.subtract(b)
    diff: List[str] = []
    for x in a:
        if count[x] > 0:
            count[x] -= 1
            diff.append(x)

    return diff

def list_intersect(a: List[str], b: List[str]):
    return list((Counter(a) & Counter(b)).elements())

def compare_testsuite_log(previous_log_path: str, current_log_path: str):
    """
    returns (resolved_failures, unresolved_failures, new_failures)
    failures: Dict[tool combination label : Dict[unique testsuite name: Set[testsuite failure log]]]
    tool combination: 'tool arch abi model'
    """
    previous_failures = parse_testsuite_failures(previous_log_path)
    current_failures = parse_testsuite_failures(current_log_path)

    assert previous_failures != None
    assert current_failures != None

    # Glibc doesn't do multilib comparisons
    if previous_failures[0] == current_failures[0]:
        libname = previous_failures[0].libname

        previous_fails = set(previous_failures[1])
        current_fails = set(current_failures[1])
        resolved_failures = (
            previous_fails - current_fails
        )
        unresolved_failures = (
            previous_fails & current_fails
        )
        new_failures = current_fails - previous_fails

        classified_glibc_failures = ClassifedGlibcFailures({libname: GlibcFailure(list(resolved_failures))}, {libname: GlibcFailure(list(unresolved_failures))}, {libname: GlibcFailure( list(new_failures))})
    else:
        # Different libnames, so all fails are unresolved fails
        classified_glibc_failures = ClassifedGlibcFailures({}, {previous_failures[0].libname: GlibcFailure(previous_failures[1]), current_failures[0].libname: GlibcFailure(current_failures[1])}, {})

    return classified_glibc_failures


def glibcfailure_to_summary(failure: Dict[LibName, GlibcFailure], failure_name: str, previous_hash: str, current_hash: str, current_hash_committed: bool):
    tools = ("glibc")
    result = f"|{failure_name}|{tools[0]}|Previous Hash|\n"
    result +="|---|---|---|\n"
    for libname, glibcfailure in failure.items():
        result += f"|{libname}|"
        # convert tuple of counts to string
        result += f"{'/'.join(glibcfailure.count_failures())}|"

        if current_hash_committed:
            result += f"[{previous_hash}](https://github.com/bminor/glibc/compare/{previous_hash}...{current_hash})|\n"
        else:
           result += f"https://github.com/bminor/glibc/commit/{previous_hash}|\n"
    result += "\n"
    return result


def failures_to_summary(failures: ClassifedGlibcFailures, previous_hash: str, current_hash: str, current_hash_committed: bool):
    result = "# Summary\n"
    result += glibcfailure_to_summary(failures.resolved, "Resolved Failures", previous_hash, current_hash, current_hash_committed)
    result += glibcfailure_to_summary(failures.unresolved, "Unresolved Failures", previous_hash, current_hash, current_hash_committed)
    result += glibcfailure_to_summary(failures.new, "New Failures", previous_hash, current_hash, current_hash_committed)
    result += "\n"
    return result


def failures_to_markdown(
    failures: ClassifedGlibcFailures, previous_hash: str, current_hash: str, current_hash_committed: bool
) -> str:
    result = f"""---
title: {previous_hash}->{current_hash}
labels: bug
---\n"""
    result += failures_to_summary(failures, previous_hash, current_hash, current_hash_committed)
    result += str(failures)
    return result


def is_result_valid(log_path: str):
    if not Path(log_path).exists():
        raise ValueError(f"Invalid Path: {log_path}")
    with open(log_path, "r") as file:
        while True:
            line = file.readline()
            if not line:
                break
            if line.startswith(
                "               ========= Summary of glibc testsuite ========="
            ):
                return True
        return False

def compare_logs(previous_hash: str, previous_log: str, current_hash: str, current_log: str, output_markdown: str, current_hash_committed: bool):
    if not is_result_valid(previous_log):
        raise RuntimeError(f"{previous_log} doesn't include Summary of the testsuite")
    if not is_result_valid(current_log):
        raise RuntimeError(f"{current_log} doesn't include Summary of the testsuite")
    failures = compare_testsuite_log(previous_log, current_log)
    markdown = failures_to_markdown(failures, previous_hash, current_hash, current_hash_committed)
    with open(output_markdown, "w") as markdown_file:
        markdown_file.write(markdown)


def main():
    args = parse_arguments()
    compare_logs(args.previous_hash, args.previous_log, args.current_hash, args.current_log, args.output_markdown, args.current_hash_committed)


if __name__ == "__main__":
    main()
