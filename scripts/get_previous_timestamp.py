import argparse
import requests
import json
import sys


def parse_arguments():
    """parse command line arguments"""
    parser = argparse.ArgumentParser(description="Get workflow information")
    parser.add_argument(
        "-token",
        required=True,
        type=str,
        help="Github access token",
    )
    parser.add_argument(
        "-rid",
        "--run-id",
        required=True,
        type=str,
        help="Github action run id",
    )
    parser.add_argument(
        "-repo",
        required=True,
        type=str,
        help="Repo to get runs from",
    )
    parser.add_argument(
        "-workflow",
        required=True,
        type=str,
        help="Workflow name",
    )
    return parser.parse_args()


def get_workflow_runs(token: str, repo: str, workflow: str):
    params = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "branch": "main",
        "event": "schedule",
        "per_page": 100,
    }
    url = f"https://api.github.com/repos/{repo}/actions/runs"
    r = requests.get(url, params)
    if r.status_code >= 500:
        with open("patchwork_down.txt", "w") as f:
            f.write(f"status code: {r.status_code}")
        return None
    run_info = json.loads(r.text)
    print(f"Before filter have {len(run_info['workflow_runs'])} to consider")
    runs = [run for run in run_info["workflow_runs"] if run["name"] == workflow]
    print(f"After filter have {len(runs)} to consider")
    return runs


def find_run_index(runs, run_id: str):
    for i, run in enumerate(runs):
        if str(run["id"]) == str(run_id):
            return i
    return None


def write_run_timestamp(runs, run_id: str, run_index: int):
    assert str(runs[run_index]["id"]) == str(run_id)
    with open("date_current.txt", "w") as f:
        f.write(runs[run_index]["created_at"])
    with open("date_prior.txt", "w") as f:
        f.write(runs[run_index + 1]["created_at"])


def write_run_id(runs, run_id: str, run_index: int):
    assert len(runs) >= 1
    assert str(runs[run_index]["id"]) == str(
        run_id
    ), f"The 10 most recent runs are: \n{runs[:10]}"
    with open("run_id.txt", "w") as f:
        f.write(str(runs[run_index + 1]["id"]))


def main():
    args = parse_arguments()
    runs = get_workflow_runs(args.token, args.repo, args.workflow)
    if not runs:
        print("Server failure. Patchwork returned status code >= 500")
        sys.exit(1)
    with open("runs.log", "w") as f:
        f.write(json.dumps(runs[:10], indent=4))
    run_index = find_run_index(runs, args.run_id)
    assert (
        run_index is not None,
        f"{args.run_id} is not found in list of the 100 most recent runs",
    )
    write_run_id(runs, args.run_id, run_index)
    write_run_timestamp(runs, args.run_id, run_index)


if __name__ == "__main__":
    main()
