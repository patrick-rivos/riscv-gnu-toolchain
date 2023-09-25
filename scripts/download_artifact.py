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
    artifact_name: str, repo_name: str, token: str, github: "Github | None" = None
) -> "str | None":
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


def download_artifact(artifact_name: str, artifact_id: str, token: str, repo: str) -> str:
    """
    Uses GitHub api endpoint to download the given artifact into ./temp/.
    Returns the path of the downloaded zip
    """
    params = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {token}",
        "X-Github-Api-Version": "2022-11-28",
    }
    response = requests.get(
        f"https://api.github.com/repos/{repo}/actions/artifacts/{artifact_id}/zip",
        headers=params,
        timeout=15 * 60,  # 15 minute timeout
    )
    print(f"download for {artifact_name}: {response.status_code}")

    artifact_zip_name = artifact_name.replace(".log", ".zip")
    artifact_zip = f"./temp/{artifact_zip_name}"

    with open(artifact_zip, "wb") as artifact:
        artifact.write(response.content)

    return artifact_zip


def extract_artifact(
    artifact_name: str, artifact_zip: str, outdir: str = "current_logs"
):
    """
    Extracts a given artifact into the outdir.
    """
    with ZipFile(artifact_zip, "r") as zf:
        zf.extractall(path="./temp/")

    nested_folder = os.path.splitext(artifact_zip)[0]

    # Move the artifact into the outdir
    # TODO: Only produce non-nested zip files
    if os.path.isdir(nested_folder):
        print("Removing the nested artifact folder")
        os.rename(
            f"{nested_folder}/{artifact_name}",
            f"./{outdir}/{artifact_name}",
        )
    else:
        print("This artifact doesn't contain a directory, moving the artifact directly")
        os.rename(
            f"./temp/{artifact_name}",
            f"./{outdir}/{artifact_name}",
        )


def main():
    args = parse_arguments()

    artifact_id = search_for_artifact(args.name, args.repo, args.token)
    if artifact_id is None:
        raise ValueError(f"Could not find artifact {args.name} in {args.repo}")

    artifact_zip = download_artifact(args.name, artifact_id, args.token, args.repo)

    extract_artifact(args.name, artifact_zip, args.outdir)


if __name__ == "__main__":
    main()
