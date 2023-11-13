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
        "-comment",
        required=True,
        type=str,
        help="Comment id",
    )
    parser.add_argument(
        "-repo",
        required=True,
        type=str,
        help="repo to pull the comment from",
    )
    parser.add_argument(
        "-baseline",
        required=True,
        type=str,
        help="Baseline hash commit",
    )
    parser.add_argument(
        "-check",
        default="Build GCC",
        type=str,
        help="what check this is for",
    )
    parser.add_argument(
        "-target",
        default="",
        type=str,
        help="target",
    )
    parser.add_argument(
        "-state",
        default="",
        type=str,
        help="target state",
    )
    parser.add_argument(
        "-failure",
        action="store_true",
        help="Check build failures",
    )
    return parser.parse_args()

def get_comment(token: str, comment: str, check: str, repo: str):
    params = {"Accept": "application/vnd.github+json",
              "Authorization": f"token {token}",
              "X-GitHub-Api-Version": "2022-11-28"}
    url = f"https://api.github.com/repos/{repo}/issues/comments/{comment}"
    r = requests.get(url, params)
    print(f"status code: {r.status_code}")
    found_comment = json.loads(r.text)
    if "body" not in found_comment.keys():
        print(f"Can't find comment body. api returned: {found_comment}")
    return found_comment

def get_current_status(comment):
    status = {}
    for line in comment['body'].split('\n'):
        print(line)
        if 'Target' in line or '---' in line or '|' not in line:
            continue
        if "Additional" in line or "## Notes" in line:
            break
        target, state = line.split('|')[1:-1]
        status[target] = state

    return status

def build_new_comment(status: Dict[str, str], check: str, baseline: str):
    result = f"## {check} Status"
    result += "\n"
    result += "|Target|Status|\n"
    result += "|---|---|\n"
    for k, v in status.items():
        result += f"|{k}|{v.strip()}|\n"
    result += "\n"
    result += "## Notes\n"
    result += f"Patch(es) were applied to the hash https://github.com/gcc-mirror/gcc/commit/{baseline}. "
    result += "If this patch commit depends on or conflicts with a recently committed patch, then these results may be outdated.\n"
    with open("comment.md", "w") as f:
        f.write(result)

def main():
    args = parse_arguments()
    comment = get_comment(args.token, args.comment, args.check, args.repo)
    if args.failure:
        status = get_current_status(comment)
        with open("current_logs/failed_build.txt", "w") as f:
            for target, state in status.items():
                if "Build failure" in state:
                    f.write(f"{target}|{state}\n")
    else:
        if comment is None:
            status = {args.target: args.state}
        else:
            status = get_current_status(comment)
            status[args.target] = args.state
        build_new_comment(status, args.check, args.baseline)

if __name__ == "__main__":
    main()
