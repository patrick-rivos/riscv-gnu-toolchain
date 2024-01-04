import argparse
import os
from collections import defaultdict
from typing import Dict, List, Set, Tuple

SUMMARIES = "./summaries"
FAILURES = "./current_logs"


def get_additional_failures(file_name: str, failure_name: str, seen_failures: Set[str]):
    """ Search for build and testsuite failures """
    result = f"|{failure_name}|Additional Info|\n"
    result += "|---|---|\n"
    file_path = os.path.join(FAILURES, f"{file_name}")
    failures: Dict[str, Set[str]] = defaultdict(set)
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, "r") as f:
            while True:
                line = f.readline().strip()
                if not line:
                    break
                artifact, comment = line.split("|")
                failures[artifact].add(comment)
        for failure, comment in failures.items():
            if failure not in seen_failures:
                result += f"|{failure}|{';'.join(comment)}|\n"
                seen_failures.add(failure)
        result += "\n"
        return result, seen_failures
    return "", seen_failures

def build_summary(failures: Dict[str, List[str]], failure_name: str):
    """ Builds table in summary section """
    tools = ("gcc", "g++", "gfortran")
    result = f"|{failure_name}|{tools[0]}|{tools[1]}|{tools[2]}|Previous Hash|\n"
    result += "|---|---|---|---|---|\n"
    result += f"{''.join(sorted(failures[failure_name.split(' ')[0]]))}"
    result += "\n"
    return result

def print_failed_tests(table: str):
    print(table.split('\n'))
    failures = table.split('\n')[2:-2]
    allowlist: List[str] = []
    for failure in failures:
        print(failure.split('|'))
        log_name = failure.split('|')[1]
        components = log_name.split('-')
        allowlist.append(f"{components[1]}:{components[2]}-{components[3]}")
    print(";".join(allowlist))
    with open("allowlist.txt", "w") as f:
        f.write(";".join(allowlist) + "\n")

def failures_to_summary(failures: Dict[str, List[str]]):
    """ Builds summary section """
    result = "# Summary\n"
    seen_failures: Set[str] = set()
    additional_result, seen_failures = get_additional_failures("failed_build.txt",
                                                               "Build Failures",
                                                               seen_failures)
    result += additional_result
    additional_result, seen_failures = get_additional_failures("failed_testsuite.txt",
                                                               "Testsuite Failures",
                                                               seen_failures)
    print_failed_tests(additional_result)
    result += additional_result

    result += build_summary(failures, "New Failures")
    result += build_summary(failures, "Resolved Failures")
    result += build_summary(failures, "Unresolved Failures")
    result += "\n"
    return result

def assign_labels(file_name: str, label: str):
    """Creates label for issue"""
    file_path = os.path.join(FAILURES, f"{file_name}")
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return label
    return ""

def failures_to_markdown(failures: Dict[str, List[str]], current_hash: str, patch_name: str, title_prefix: str):
    result = f"""---
title: {title_prefix} {current_hash if patch_name == "" else patch_name}
"""
    labels: Set[str] = set()
    labels.add(assign_labels("failed_build.txt", "build-failure"))
    labels.add(assign_labels("failed_testsuite.txt", "testsuite-failure"))
    if len(failures["New"]) > 0:
        labels.add("new-regressions")
    if len(failures["Resolved"]) > 0:
        labels.add("resolved-regressions")
    if "" in labels:
        labels.remove("")
    if len(labels) > 0:
        result += f"labels: {', '.join(labels)}\n"
    with open("./labels.txt", "w") as f:
        f.write(f"{','.join(labels)}")
    result += "---\n\n"
    result += failures_to_summary(failures)
    return result

def parse_arch_info(name: str, target: str):
    """
    Extract libc, arch, abi, multilib from file name
    """
    parts = [name.split("-")[1]]
    target_parts = target.split(" ")
    parts = parts + target_parts
    return " ".join(parts)

def get_common_intersection(failures: Dict[str, Dict[str, Set[str]]]) -> Tuple[Set[str], int]:
    """
    get common failures across all affected targets (ones that appear in the tables)
    """
    common = [i for v in failures.values() for i in v.values() if len(i) != 0]
    if len(common) == 0:
        return set(), 0
    # Get the intersection of all the sets in the list
    intersect: Set[str] = set.intersection(*common)
    return intersect, len(common)

def get_unique_failures(failure_type: str, intersect: Set[str], failures: Dict[str, Dict[str, Set[str]]]):
    """
    get set difference between common failures and failures for target libc/arch/abi
    """
    result = ""
    additional_failures = False
    for file_name, all_failures in failures.items():
        for target, target_failures in all_failures.items():
            diff = target_failures - intersect
            if len(diff) > 0:
                if not additional_failures:
                    result += f"## Architecture Specific {failure_type} Failures\n"
                    additional_failures = True
                arch_info = parse_arch_info(file_name, target.strip())
                result += f"{arch_info}:\n"
                result += "```\n"
                result += "".join(sorted(list(diff)))
                result += "```\n"
    return result

def additional_failures_to_markdown(failure_type: str,
                                    failures: Dict[str, Dict[str, Set[str]]],
                                    num_targets: int):
    """
    Adds new sections to issue displaying what failures were added/resolved
    """
    intersect, num_failures = get_common_intersection(failures)
    result = ""
    if len(intersect) > 0:
        found_failures = sorted(list(intersect))
        result = f"## {failure_type} Failures Across All Affected Targets ({num_failures} targets / {num_targets} total targets)\n"
        result += "```\n"
        result += "".join(found_failures)
        result += "```\n"
    result += get_unique_failures(failure_type, intersect, failures)
    result += "\n"
    return result

def aggregate_summary(failures: Dict[str, List[str]], file_name: str):
    """
    Reads file and adds the new failures to the current
    list of failures
    """
    with open(file_name, "r") as f:
        while True:
            line = f.readline()
            if not line or line.startswith("# Summary"):
                break
        while True:
            line = f.readline()
            if not line or line.startswith("# Resolved Failures"):
                # exited Summary section and going to Resolved Failures section
                # TODO: add support for consolidating these sections
                break
            if "Failures" in line:
                index = line.split("Failures")[0][1:-1]
                continue
            if line != "\n" and "---" not in line:
                cells = line.split("|")
                if "linux" in file_name:
                    cells[1] = "linux: " + cells[1]
                else:
                    cells[1] = "newlib: " + cells[1]

                # Apply nicknames

                cells[1] = cells[1].replace("gc_zba_zbb_zbc_zbs_zfa", " Bitmanip")
                cells[1] = cells[1].replace("gc_zba_zbb_zbc_zbs", " Bitmanip")
                cells[1] = cells[1].replace("gcv_zvbb_zvbc_zvkg_zvkn_zvknc_zvkned_zvkng_zvknha_zvknhb_zvks_zvksc_zvksed_zvksg_zvksh_zvkt", " Vector Crypto")
                cells[1] = cells[1].replace("rv64imafdcv_zicond_zawrs_zbc_zvkng_zvksg_zvbb_zvbc_zicsr_zba_zbb_zbs_zicbom_zicbop_zicboz_zfhmin_zkt", "RVA23U64 profile")
                failures[index].append("|".join(cells))
        # begin resolved failures
        resolved: Dict[str, Set[str]] = defaultdict(set)
        cur_target = None
        while True:
            line = f.readline()
            if not line or line.startswith("# Unresolved Failures"):
                break
            temp_comps = line.split(" ")
            if temp_comps[0] == "##":
                cur_target = " ".join(temp_comps[1:]).strip()
                continue
            if temp_comps[0] == "###":
                continue
            if line != "\n":
                resolved[cur_target].add(line)
        # begin unresolved failures
        while True:
            line = f.readline()
            if not line or line.startswith("# New Failures"):
                break
        # begin new failures
        new: Dict[str, Set[str]] = defaultdict(set)
        cur_target = None
        while True:
            line = f.readline()
            if not line:
                break
            temp_comps = line.split(" ")
            if temp_comps[0] == "##":
                cur_target = " ".join(temp_comps[1:]).strip()
                continue
            if temp_comps[0] == "###":
                continue
            if line != "\n":
                new[cur_target].add(line)

    return failures, resolved, new

def parse_arguments():
    parser = argparse.ArgumentParser(description="Testsuite Compare Options")
    parser.add_argument(
        "-chash",
        "--current-hash",
        metavar="<string>",
        required=True,
        type=str,
        help="Commit hash of the current GCC testsuite log",
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
        "-patch",
        "--patch-name",
        default="",
        metavar="<string>",
        type=str,
        help="Patch name",
    )
    parser.add_argument(
        "-title",
        "--title-prefix",
        default="Testsuite Status",
        metavar="<string>",
        type=str,
        help="Title prefix",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    failures: Dict[str, List[str]] = { "Resolved": [], "Unresolved": [], "New": [] }
    all_resolved: Dict[str, Dict[str, Set[str]]] = {}
    all_new: Dict[str, Dict[str, Set[str]]] = {}
    for file in os.listdir(SUMMARIES):
        failures, resolved, new = aggregate_summary(failures, os.path.join(SUMMARIES, file))
        all_resolved[file] = resolved
        all_new[file] = new

    print([i.keys() for i in all_new.values()])
    summary_markdown = failures_to_markdown(failures, args.current_hash, args.patch_name, args.title_prefix)
    resolved_markdown = additional_failures_to_markdown("Resolved",
                                                        all_resolved,
                                                        len(failures['Unresolved']))
    new_markdown = additional_failures_to_markdown("New", all_new,
                                                   len(failures['Unresolved']))

    markdown = summary_markdown + new_markdown + resolved_markdown

    with open(args.output_markdown, "w") as markdown_file:
        markdown_file.write(markdown)

if __name__ == "__main__":
    main()
