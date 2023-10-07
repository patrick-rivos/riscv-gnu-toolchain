import argparse
import requests
import json

def parse_arguments():
    """ parse command line arguments """
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
    return parser.parse_args()

def get_workflow_runs(token: str, repo: str):
    params = {"Accept": "application/vnd.github+json",
              "Authorization": f"token {token}",
              "X-GitHub-Api-Version": "2022-11-28",
              "branch": "patchworks-ci",
              "event": "schedule"}
    url = "https://api.github.com/repos/{repo}/actions/runs"
    r = requests.get(url, params)
    runs = json.loads(r.text)
    return runs

def get_run_timestamp(runs, run_id: str):
    with open("date_cur.txt", "w") as f:
        if str(runs[0]['id']) != str(run_id):
            f.write(runs[0]['created_at'])
        else:
            f.write(runs[1]['created_at'])


def main():
    args = parse_arguments()
    runs = get_workflow_runs(args.token, args.repo)
    with open("runs.log", "w") as f:
        f.write(json.dumps(runs['workflow_runs'][:10], indent=4))
    get_run_timestamp(runs['workflow_runs'], args.run_id)

if __name__ == "__main__":
    main()
