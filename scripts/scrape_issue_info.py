import argparse
import requests
import json

def parse_arguments():
    """ parse command line arguments """
    parser = argparse.ArgumentParser(description="Get issue information")
    parser.add_argument(
        "-num",
        required=True,
        type=str,
        help="Issue number to get information for",
    )
    parser.add_argument(
        "-token",
        required=True,
        type=str,
        help="Github access token",
    )
    return parser.parse_args()

def get_issue_hash(issue_num: str, token: str):
    issue_url = f"https://api.github.com/repos/patrick-rivos/riscv-gnu-toolchain/issues/{issue_num}"
    params = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {token}",
        "X-Github-Api-Version": "2022-11-28",
    }
    r = requests.get(issue_url, headers=params)
    response = json.loads(r.text)
    print(response["title"].split(" ")[-1])

def main():
    args = parse_arguments()
    issue_hash = get_issue_hash(args.num, args.token)

if __name__ == '__main__':
    main()
