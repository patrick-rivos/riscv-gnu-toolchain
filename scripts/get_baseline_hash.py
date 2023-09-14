import requests
import json
import argparse

def parse_arguments():
    """ parse command line arguments """
    parser = argparse.ArgumentParser(description="Download valid log artifacts")
    parser.add_argument(
        "-token",
        required=True,
        type=str,
        help="Github access token",
    )
    return parser.parse_args()

def parse_baseline_hash(url: str, token: str):
    params = {"Accept": "application/vnd.github+json",
              "Authorization": f"token {token}",
              "X-GitHub-Api-Version": "2022-11-28"}
    r = requests.get(url, params=params)
    issues = json.loads(r.text)
    issue = issues[0]
    print(issue["title"].split(" ")[-1], end="")
    

def main():
    args = parse_arguments()
    url = "https://api.github.com/repos/patrick-rivos/riscv-gnu-toolchain/issues?page=1&q=is%3Aissue+-label%3Abisect+-label%3Abuild-failure+-label%3Atestsuite-failure"
    parse_baseline_hash(url, args.token)

if __name__ == '__main__':
    main()
