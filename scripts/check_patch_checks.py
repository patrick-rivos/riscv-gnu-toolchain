import argparse
import requests
import json
import os
from collections import defaultdict
from typing import Dict, List, Set


def parse_arguments():
    parser = argparse.ArgumentParser(description="Create Patch Files")
    parser.add_argument(
        "-start",
        "--start",
        metavar="<string>",
        type=str,
        help="Start timestamp for patches",
    )
    parser.add_argument(
        "-end",
        "--end",
        metavar="<string>",
        type=str,
        help="End timestamp for patches",
    )
    return parser.parse_args()


def make_api_request(url):
    print(url)
    r = requests.get(url)
    return r.headers, json.loads(r.text)


def check_patch(patch):
    url = patch["checks"]
    # Check if patch has been seen by ci
    checks = [
        check
        for check in make_api_request(url)[1]
        if check["user"]["username"] == "rivoscibot"
    ]

    # first three checks should be lint start/finish and apply
    if len(checks) < 3:
        return True

    apply_failure = False
    testsuite_reported = False

    for check in checks:
        if check["description"] == "Patch failed to apply":
            apply_failure = True
        if check["context"] == "toolchain-ci-rivos-test":
            testsuite_report = True

    # If testsuite was not reported, mark for rerun
    # testsuite should be reported as long as it was applied
    # and run has completed (enough time has passed)
    if apply_failure and testsuite_reported:
        return True

    return False


def get_patches(start: str, end: str):
    page_num = 1
    patches = []
    while True:
        url = f"https://patchwork.sourceware.org/api/1.3/patches/?order=date&q=RISC-V&project=6&since={start}&before={end}&page={page_num}"
        headers, page = make_api_request(url)
        patches += page
        if 'rel="next"' not in headers["Link"]:
            break
        page_num += 1

    print([patch["id"] for patch in patches])

    to_run = [str(patch["id"]) for patch in patches if check_patch(patch)]
    print(to_run)
    if to_run:
        with open("patch_numbers_to_run.txt", "w") as f:
            nums = " ".join(to_run)
            f.write(nums)


def main():
    args = parse_arguments()
    get_patches(args.start, args.end)


if __name__ == "__main__":
    main()
