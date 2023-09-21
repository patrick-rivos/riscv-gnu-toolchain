import argparse
import os
from zipfile import ZipFile
from github import Auth, Github
import requests


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Download single log artifact")
    parser.add_argument(
        "-name",
        required=True,
        type=str,
        help="Name of the artifact",
    )
    parser.add_argument(
        "-repo", required=True, type=str, help="Github repo to search/download in"
    )
    parser.add_argument(
        "-token",
        required=True,
        type=str,
        help="Github access token",
    )
    parser.add_argument(
        "-outdir", required=True, type=str, help="Output dir to put downloaded file"
    )
    return parser.parse_args()


def search_for_artifact(
    artifact_name: str, repo_name: str, token: str, github: Github | None = None
) -> str | None:
    """
    Search for the given artifact.
    If multiple artifacts with that name exist, grab the first returned by the
    API.
    Returns the artifact's id or None if the artifact was not found.
    """
    if github is None:
        auth = Auth.Token(token)
        github = Github(auth=auth)

    repo = github.get_repo(repo_name)

    artifacts = repo.get_artifacts(artifact_name).get_page(0)
    if len(artifacts) != 0:
        return str(artifacts[0].id)

    return None


def download_artifact(
    artifact_name: str, artifact_id: str, token: str, outdir: str = "current_logs"
):
    """
    Uses GitHub api endpoint to download and extract the previous workflow
    log artifacts into the given outdir.
    """
    params = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {token}",
        "X-Github-Api-Version": "2022-11-28",
    }
    artifact_zip_name = artifact_name.replace(".log", ".zip")
    response = requests.get(
        f"https://api.github.com/repos/patrick-rivos/riscv-gnu-toolchain/actions/artifacts/{artifact_id}/zip",
        headers=params,
        timeout=15 * 60,  # 15 minute timeout
    )
    print(f"download for {artifact_zip_name}: {response.status_code}")
    download_binary = False

    with open(f"./temp/{artifact_zip_name}", "wb") as artifact:
        artifact.write(response.content)

    with ZipFile(f"./temp/{artifact_zip_name}", "r") as zf:
        try:
            zf.extractall(path=f"./temp/{artifact_name.split('.log')[0]}")
        except NotADirectoryError:
            download_binary = True
            print("extracting a binary file")
            zf.extractall(path="./temp/")

    if not download_binary:
        os.rename(
            f"./temp/{artifact_name.split('.log')[0]}/{artifact_name}",
            f"./{outdir}/{artifact_name}",
        )


def main():
    args = parse_arguments()

    artifact_id = search_for_artifact(args.name, args.repo, args.token)
    if artifact_id is None:
        raise ValueError(f"Could not find artifact {args.name} in {args.repo}")

    download_artifact(args.name, artifact_id, args.token, args.outdir)


if __name__ == "__main__":
    main()
