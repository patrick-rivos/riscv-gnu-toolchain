import argparse
import requests
import json

from datetime import datetime

def parse_arguments():
    """ parse command line arguments """
    parser = argparse.ArgumentParser(description="Auto close issues")
    parser.add_argument(
        "-token",
        required=True,
        type=str,
        help="Github access token",
    )
    return parser.parse_args()

def get_issues(token: str):
    params = {"Accept": "application/vnd.github+json",
              "Authorization": f"token {token}",
              "X-GitHub-Api-Version": "2022-11-28"}
    url = f"https://api.github.com/repos/ewlu/gcc-precommit-ci/issues?per_page=100&state=open"
    r = requests.get(url, params)
    issues = json.loads(r.text)
    filtered = [issue for issue in issues if 'pull_request' not in issue.keys()]
    return filtered

def get_patch_id(issue):
    body = issue["body"].split("\n")
    for line in body():
        if line == "":
            continue
        if "Patch id:" in line:
            patch_id = line.split(":")[-1].strip()
            return patch_id
    return None

def get_patch_state(patch_id: str):
    url = f"https://patchwork.sourceware.org/api/1.3/patches/{patch_id}"
    r = requests.get(url)
    details = json.loads(r.text)
    return details["state"]

def check_issue_is_closable(issue):
    patch_id = get_patch_id(issue)
    if patch_id is None:
        return False
    patch_state = get_patch_state(patch_id)
    if patch_state != "committed" and patch_state != "superseded":
        return False
    created_time = datetime.strptime(issue["created_at"], "%Y-%m-%dT%H:%M:%SZ") 
    now = datetime.now()
    diff = now - created_time
    if diff.days < 7:
        return False
    return True

def close_issue(issue_number: int, token: str):
    params = {"Accept": "application/vnd.github+json",
              "Authorization": f"token {token}",
              "X-GitHub-Api-Version": "2022-11-28"}
    url = f"https://api.github.com/repos/ewlu/gcc-precommit-ci/issues/{issue_number}"
    data = {"state": "closed"}
    r = requests.patch(url=url, data=json.dumps(data), headers=params)
    print(f"closing issue: {issue_number}")
    print(r.status_code)
    print(r.text)

def main():
    args = parse_arguments()
    issues = get_issues(args.token)
    for issue in issues:
        if check_issue_is_closable(issue):
            close_issue(issue["number"], args.token)

if __name__ == "__main__":
    main()

