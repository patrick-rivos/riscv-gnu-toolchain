import argparse
import json
import requests
import os
from typing import List, Tuple


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Download valid log artifacts")
    parser.add_argument(
        "-repo",
        required=True,
        type=str,
        help="Name of the repo to download from",
    )
    parser.add_argument(
        "-token",
        required=True,
        type=str,
        help="Github access token",
    )
    parser.add_argument(
        "-prefix",
        required=False,
        default="",
        type=str,
        help="Artifact prefix",
    )

    return parser.parse_args()


def filter_issue(issue):
    title_check = "Testsuite Status" in issue["title"]
    issue_labels = issue["labels"]
    filter_labels = ["staging", "bisect", "coord", "invalid"]
    labels_check = True
    for label in issue_labels:
        if label["name"] in filter_labels:
            labels_check = False
            break
    if 'pull_request' not in issue.keys() and labels_check and title_check:
        return True
    return False


def remove_duplicates(issues):
    # remove issues with the same name preserving the oldest one
    issues.reverse()
    reversed_issues = []
    [reversed_issues.append(issue) for issue in issues if issue not in reversed_issues]
    reversed_issues.reverse()
    return reversed_issues


def issue_hashes(repo_name: str, token: str):
    params = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {token}",
        "X-Github-Api-Version": "2022-11-28",
    }
    response = requests.get(
        f"https://api.github.com/repos/{repo_name}/issues?page=1&per_page=100&state=all",
        headers=params,
        timeout=15 * 60, # 15 min timeout
    )
    print(f"getting most recent 100 issues: {response.status_code}")
    issues = json.loads(response.text)
    filtered_issues = [issue for issue in issues if filter_issue(issue)]
    filtered_issues = remove_duplicates(filtered_issues)
    issue = filtered_issues[4]
    with open("issue_hash.txt", "w") as f:
        f.write(issue["title"].split(" ")[-1])

    with open("issue_number.txt", "w") as f:
        f.write(str(issue["number"]))


def main():
    args = parse_arguments()
    issue_hashes(args.repo, args.token)


if __name__ == "__main__":
    main()
