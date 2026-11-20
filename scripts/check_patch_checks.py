import argparse
import os

import requests

from riscv_patch_scope import GCC_PROJECT, is_gcc_riscv_patch


PATCHWORK_TEST_CONTEXT = "toolchain-ci-rise-test"
PATCHWORK_FINAL_STATES = {"success", "fail", "warning"}


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
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.headers, response.json()


def get_patchwork_check_username():
    username = os.environ.get("PATCHWORK_CHECK_USERNAME", "").strip()
    if not username:
        raise RuntimeError(
            "PATCHWORK_CHECK_USERNAME must name the Patchwork account used by CI"
        )
    return username


def check_patch(patch, check_username=None):
    url = patch["checks"]
    if check_username is None:
        check_username = get_patchwork_check_username()
    # Check if patch has been seen by ci
    checks = [
        check
        for check in make_api_request(url)[1]
        if check["user"]["username"] == check_username
    ]

    # first three checks should be lint start/finish and apply
    if len(checks) < 3:
        return True

    apply_failure = False
    testsuite_reported = False

    for check in checks:
        if check["description"] == "Patch failed to apply":
            apply_failure = True
        if (
            check["context"] == PATCHWORK_TEST_CONTEXT
            and check.get("state") in PATCHWORK_FINAL_STATES
        ):
            testsuite_reported = True

    # If testsuite was not reported, mark for rerun
    # testsuite should be reported as long as it was applied
    # and run has completed (enough time has passed)
    return not apply_failure and not testsuite_reported


def get_patches(start: str, end: str):
    check_username = get_patchwork_check_username()
    page_num = 1
    patches = []
    while True:
        url = f"https://patchwork.sourceware.org/api/1.3/patches/?order=date&project={GCC_PROJECT}&since={start}&before={end}&page={page_num}"
        headers, page = make_api_request(url)
        patches += page
        if 'rel="next"' not in headers.get("Link", ""):
            break
        page_num += 1

    print([patch["id"] for patch in patches])

    to_run = [
        str(patch["id"])
        for patch in patches
        if is_gcc_riscv_patch(patch) and check_patch(patch, check_username)
    ]
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
