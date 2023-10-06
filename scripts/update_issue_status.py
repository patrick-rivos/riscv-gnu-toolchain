import requests
import argparse
import json
from typing import Dict, List, Set

def parse_arguments():
    """ parse command line arguments """
    parser = argparse.ArgumentParser(description="Download valid log artifacts")
    parser.add_argument(
        "-token",
        required=True,
        type=str,
        help="Github access token",
    )
    parser.add_argument(
        "-patch",
        required=True,
        type=str,
        help="Patch name",
    )
    parser.add_argument(
        "-check",
        required=True,
        type=str,
        help="what check this is for",
    )
    parser.add_argument(
        "-target",
        required=True,
        type=str,
        help="target",
    )
    parser.add_argument(
        "-state",
        required=True,
        type=str,
        help="target state",
    )
    parser.add_argument(
        "-repo",
        required=True,
        type=str,
        help="repo to pull the issues from",
    )
    return parser.parse_args()

def get_issue(token: str, patch: str, check: str, repo: str):
    params = {"Accept": "application/vnd.github+json",
              "Authorization": f"token {token}",
              "X-GitHub-Api-Version": "2022-11-28"}
    url = f"https://api.github.com/repos/{repo}/issues?page=1&q=is%3Aissue&state=all"
    r = requests.get(url, params)
    issues = json.loads(r.text)
    found_issue = None
    for issue in issues:
        if patch in issue["title"] and check in issue["title"]:
            found_issue = issue
            break
    return found_issue

def get_current_status(issue):
    status = {}
    for line in issue['body'].split('\n'):
        print(line)
        if 'Target' in line or '---' in line or '|' not in line:
            continue
        if "Associated" in line:
            break
        target, state = line.split('|')[1:-1]
        status[target] = state

    return status

def build_new_issue(status: Dict[str, str], patch: str, check: str):
    result = f"---\ntitle: {check} Status {patch}\n---\n"
    result += "|Target|Status|\n"
    result += "|---|---|\n"
    for k, v in status.items():
        result += f"|{k}|{v.strip()}|\n"
    result += "\n"
    with open("issue.md", "w") as f:
        f.write(result)

def main():
    args = parse_arguments()
    issue = get_issue(args.token, args.patch, args.check, args.repo)
    if issue is None:
        status = {args.target: args.state}
    else:
        status = get_current_status(issue)
        status[args.target] = args.state
    build_new_issue(status, args.patch, args.check)

if __name__ == "__main__":
    main()
