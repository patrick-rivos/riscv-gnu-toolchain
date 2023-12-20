import argparse
import requests
import json
import sys

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
    parser.add_argument(
        "-workflow",
        required=True,
        type=str,
        help="Workflow name",
    )
    return parser.parse_args()

def get_workflow_runs(token: str, repo: str, workflow: str):
    params = {"Accept": "application/vnd.github+json",
              "Authorization": f"token {token}",
              "X-GitHub-Api-Version": "2022-11-28",
              "branch": "main",
              "event": "schedule",
              "per_page": 100}
    url = f"https://api.github.com/repos/{repo}/actions/runs"
    r = requests.get(url, params)
    if r.status_code >= 500:
        with open("patchwork_down.txt", "w") as f:
            f.write(f"status code: {r.status_code}")
        return None
    runs = [run for run in json.loads(r.text) if run["name"] == workflow]
    print(f"After filter have {len(runs)} to consider")
    return runs

def write_run_timestamp(runs, run_id: str):
    with open("date_cur.txt", "w") as f:
        if str(runs[0]['id']) != str(run_id):
            f.write(runs[0]['created_at'])
        else:
            f.write(runs[1]['created_at'])

def write_run_id(runs, run_id: str):
    with open("run_id.txt", "w") as f:
        if str(runs[0]['id']) != str(run_id):
            f.write(runs[0]['id'])
        else:
            f.write(runs[1]['id'])

def main():
    args = parse_arguments()
    runs = get_workflow_runs(args.token, args.repo, args.workflow)
    if runs == None:
        print("Server failure. Patchwork returned status code >= 500")
        sys.exit(1)
    with open("runs.log", "w") as f:
        f.write(json.dumps(runs['workflow_runs'][:10], indent=4))
    write_run_timestamp(runs['workflow_runs'], args.run_id)
    write_run_id(runs['workflow_runs'], args.run_id)

if __name__ == "__main__":
    main()
