import argparse
import requests
import json
import sys
import datetime


def parse_arguments():
    """parse command line arguments"""
    parser = argparse.ArgumentParser(description="Get workflow information")
    parser.add_argument(
        "-token",
        required=False,
        default="",
        type=str,
        help="Github access token",
    )
    parser.add_argument(
        "-rid",
        "--run-id",
        required=False,
        default="",
        type=str,
        help="Github action run id",
    )
    parser.add_argument(
        "-repo",
        required=False,
        default="",
        type=str,
        help="Repo to get runs from",
    )
    parser.add_argument(
        "-timestamp",
        required=False,
        default="",
        type=str,
        help="current time",
    )
    parser.add_argument(
        "-workflow",
        required=False,
        default="",
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


def truncate_to_15_minutes(timestamp_str: str):
    timestamp = datetime.datetime.fromisoformat(timestamp_str)

    minutes = timestamp.minute
    remainder = minutes % 15
    timestamp = timestamp.replace(minute=minutes - remainder, second=0, microsecond=0)
    print(f"rounded timestamp {timestamp_str} to {timestamp.isoformat()}")
    return timestamp


def write_timestamps(ctime: str, ptime: str = ""):
    current_timestamp = truncate_to_15_minutes(ctime)
    if ptime == "":
        prior_timestamp = current_timestamp - datetime.timedelta(minutes=15)
    else:
        prior_timestamp = truncate_to_15_minutes(ptime)

    prior_minus_15_timestamp = prior_timestamp - datetime.timedelta(minutes=15)

    print(
        f"""
         current_timestamp rounded: {current_timestamp.isoformat()}
         prior_timestamp rounded: {prior_timestamp.isoformat()}
         prior_minus_15_timestamp rounded: {prior_minus_15_timestamp.isoformat()}
         """
    )

    with open("current_time_rounded.txt", "w") as f:
        f.write(current_timestamp.isoformat())

    with open("prior_run_time_rounded.txt", "w") as f:
        f.write(prior_timestamp.isoformat())

    with open("prior_run_time_minus_15_min_rounded.txt", "w") as f:
        f.write(prior_minus_15_timestamp.isoformat())


def write_run_id(runs, run_id: str, run_index: int):
    assert len(runs) >= 1
    assert str(runs[run_index]["id"]) == str(
        run_id
    ), f"The 10 most recent runs are: \n{runs[:10]}"
    with open("run_id.txt", "w") as f:
        f.write(str(runs[run_index + 1]["id"]))


def main():
    args = parse_arguments()
    if args.timestamp == "":
        runs = get_workflow_runs(args.token, args.repo, args.workflow)
        if not runs:
            print("Server failure. Patchwork returned status code >= 500")
            sys.exit(1)
        with open("runs.log", "w") as f:
            f.write(json.dumps(runs[:10], indent=4))
        run_index = find_run_index(runs, args.run_id)
        assert run_index is not None, f"{args.run_id} is not found in list of the 100 most recent runs"
        write_run_id(runs, args.run_id, run_index)
        assert str(runs[run_index]["id"]) == str(args.run_id)
        # The created_at has an extra Z at the end of the isoformat-ed
        # timestamp this causes the output timestamp to have an additional
        # +00:00 appended to the rounded timestamps which breaks
        # create_patches_files.py api request
        write_timestamps(runs[run_index]["created_at"][:-1], runs[run_index + 1]["created_at"][:-1])
    else:
        write_timestamps(args.timestamp)


if __name__ == "__main__":
    main()
