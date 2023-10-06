import requests
import argparse
from typing import Dict

def parse_arguments():
    parser = argparse.ArgumentParser(description="Send api response")
    parser.add_argument(
        "-pid",
        "--patch-id",
        metavar="<string>",
        required=True,
        type=str,
        help="Patch id",
    )
    parser.add_argument(
        "-desc",
        "--description",
        metavar="<string>",
        required=True,
        type=str,
        help="Check type (linter, build, etc)",
    )
    parser.add_argument(
        "-token",
        "--token",
        metavar="<string>",
        required=True,
        type=str,
        help="Patchworks api token",
    )
    parser.add_argument(
        "-state",
        "--state",
        metavar="<string>",
        default="pending",
        type=str,
        help="check state",
    )
    parser.add_argument(
        "-context",
        "--context",
        required=True,
        metavar="<string>",
        type=str,
        help="What test we reporting for",
    )
    parser.add_argument(
        "-rid",
        "--run-id",
        metavar="<string>",
        type=str,
        help="run id",
    )
    parser.add_argument(
        "-iid",
        "--issue-id",
        metavar="<string>",
        type=str,
        help="issue number",
    )
    parser.add_argument(
        "-comment",
        action="store_true",
        help="is comment",
    )
    return parser.parse_args()

def create_data(desc: str, issue: str, rid: str, state: str, context: str):
    target_url = None
    if issue is None or issue == "":
        target_url = f"https://github.com/ewlu/riscv-gnu-toolchain/actions/runs/{rid}"
    else:
        target_url = f"https://github.com/ewlu/riscv-gnu-toolchain/issues/{issue}"
    data = {
        "state": state,
        "target_url": target_url,
        "context": f"toolchain-ci-rivos-{context}",
        "description": desc
    }
    return data

def create_headers(token: str):
    headers = { "Authorization": f"Token {token}" }
    return headers


def send(patch_id: str, data: Dict[str, str], headers: Dict[str, str]):
    url = f"https://patchwork.sourceware.org/api/1.3/patches/{patch_id}/checks/"

    print("is comment. making post request")

    response = requests.post(url, data=data, headers=headers)
    print(response.status_code)
    print(response.text)

def main():
    args = parse_arguments()
    data = create_data(args.description, args.issue_id, args.run_id, args.state, args.context)
    headers = create_headers(args.token)
    print(f"data: {data}")
    print(args.comment)
    if args.comment:
        send(args.patch_id, data, headers)

if __name__ == "__main__":
    main()
