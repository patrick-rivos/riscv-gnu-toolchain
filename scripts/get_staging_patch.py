import argparse
import json
import requests
import re


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

    return parser.parse_args()


def filter_issue(issue):
    title_check = issue["title"].split("-")[-1] == "1"
    issue_labels = [label['name'] for label in issue["labels"]]
    labels_check = "valid-baseline" in issue_labels
    if "pull_request" not in issue.keys() and labels_check and title_check:
        return True
    return False


def get_issue(repo_name: str, token: str):
    params = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {token}",
        "X-Github-Api-Version": "2022-11-28",
    }
    response = requests.get(
        f"https://api.github.com/repos/{repo_name}/issues?page=1&per_page=100&state=closed",
        headers=params,
        timeout=15 * 60,  # 15 min timeout
    )
    print(f"getting most recent 100 issues: {response.status_code}")
    issues = json.loads(response.text)
    filtered_issues = [issue for issue in issues if filter_issue(issue)]
    issue = filtered_issues[0]
    return issue


def get_comment(repo_name: str, token: str, issue_num: int):
    params = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {token}",
        "X-Github-Api-Version": "2022-11-28",
    }
    response = requests.get(
        f"https://api.github.com/repos/{repo_name}/issues/{issue_num}/comments",
        headers=params,
        timeout=15 * 60,  # 15 min timeout
    )
    print(f"getting comments for issue {issue_num}: {response.status_code}")
    comments = json.loads(response.text)
    assert len(comments) > 2
    return comments[1]


def parse_patch_id_from_body(body: str):
    pattern = "Patch id: \d+"
    match = re.search(pattern, body).group()
    print(f"Parsed: '{match}' from issue body")
    return match.split(" ")[-1]


def parse_hash_from_body(body: str, hash_type: str):
    pattern = f"{hash_type}: [^|]*"
    match = re.search(pattern, body).group()
    print(f"Parsed: '{match}' for {hash_type} from comment body")
    return match.split("/")[-1]


def parse_info(issue, comment):
    issue_body = issue["body"]
    comment_body = comment["body"]
    patch_id = parse_patch_id_from_body(issue_body)
    baseline = parse_hash_from_body(comment_body, "Baseline hash")
    tip_of_tree = parse_hash_from_body(comment_body, "Tip of tree hash")
    return patch_id, baseline, tip_of_tree


def get_patch_timestamp(patch_id: str):
    url = f"https://patchwork.sourceware.org/api/1.3/patches/{patch_id}"
    r = requests.get(url)
    patch = json.loads(r.text)
    return patch["date"]


def main():
    args = parse_arguments()
    issue = get_issue(args.repo, args.token)
    issue_num = issue["number"]
    comment = get_comment(args.repo, args.token, issue_num)
    patch_id, baseline, tip_of_tree = parse_info(issue, comment)
    timestamp = get_patch_timestamp(patch_id)
    with open("patch_id.txt", "w") as f:
        f.write(str(patch_id))

    with open("baseline_hash.txt", "w") as f:
        f.write(str(baseline))

    with open("tot_hash.txt", "w") as f:
        f.write(str(tip_of_tree))

    with open("timestamp.txt", "w") as f:
        f.write(str(timestamp))

    with open("issue_num.txt", "w") as f:
        f.write(str(issue_num))


if __name__ == "__main__":
    main()
