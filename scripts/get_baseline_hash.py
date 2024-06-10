import requests
import json
import argparse
import re

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

def filter_results(issue):
    issue_labels = issue['labels']
    labels_check = True
    filter_labels = ['build-failure', 'testsuite-failure', 'bisect']
    for label in issue_labels:
        if label['name'] in filter_labels:
            labels_check = False
            break
    title_check = re.search("^Testsuite Status [0-9a-f]{40}$", issue["title"]) is not None # re.search returns None if pattern not found
    if 'pull_request' not in issue.keys() and labels_check and title_check:
        return True

def parse_baseline_hash(url: str, token: str):
    params = {"Accept": "application/vnd.github+json",
              "Authorization": f"token {token}",
              "X-GitHub-Api-Version": "2022-11-28"}
    r = requests.get(url, params=params)
    issues = json.loads(r.text)
    filtered = [issue for issue in issues if filter_results(issue)]
    issue = filtered[0]
    print(f"Baseline from {issue['title']}")
    assert(re.search("^Testsuite Status [0-9a-f]{40}$", issue["title"]) is not None) # re.search returns None if pattern not found
    with open("./baseline.txt", "w") as f:
        f.write(issue["title"].split(" ")[-1])

def main():
    args = parse_arguments()
    all_issues_url = "https://api.github.com/repos/patrick-rivos/gcc-postcommit-ci/issues?state=all&per_page=100"
    parse_baseline_hash(all_issues_url, args.token)

if __name__ == '__main__':
    main()
