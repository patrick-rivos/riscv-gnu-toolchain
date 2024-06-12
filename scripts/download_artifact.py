import argparse
import os
import requests

from pathlib import Path
from zipfile import ZipFile
from github import Auth, Github
from tempfile import TemporaryDirectory
from shutil import move

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


def download_artifact(artifact_name: str, artifact_id: str, token: str, repo: str, output_dir: str) -> str:
    """
    Uses GitHub api endpoint to download the given artifact into output_dir.
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

    # Create missing output_dir
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    # Write artifact to designated path
    artifact_zip = f"{str(output_dir_path.resolve())}/{artifact_zip_name}"
    with open(artifact_zip, "wb") as artifact:
        artifact.write(response.content)
    return artifact_zip


def extract_artifact(artifact_zip: str, outdir: str = "current_logs"
):
    """
    Extracts a given artifact into the outdir.
    """
    with TemporaryDirectory() as tmpdir:
        # Extract all the contents to the temporary directory for easier cleanup
        with ZipFile(artifact_zip, "r") as zf:
            zf.extractall(path=tmpdir)
        tmpdir_path = Path(f"{tmpdir}")
        # Artifact consists of either 1. files (normally a zip file) 2. Directory
        # Case 1
        artifact_path = tmpdir_path

        # The name of the directory always follows the zip file name. Thus use stem attribute for convenience
        directory_path = Path(f"{tmpdir}/{Path(artifact_zip).stem}")
        # Case 2
        if directory_path.exists():
            artifact_path = directory_path

        # Create missing outdir
        output_dir_path = Path(outdir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        # Move all the files/directory unzipped from the artifact
        for file in artifact_path.iterdir():
            move(str(file), outdir)


def main():
    args = parse_arguments()

    artifact_id = search_for_artifact(args.name, args.repo, args.token)
    if artifact_id is None:
        raise ValueError(f"Could not find artifact {args.name} in {args.repo}")

    with TemporaryDirectory() as tmpdir:
        artifact_zip = download_artifact(args.name, artifact_id, args.token, args.repo, tmpdir)
        extract_artifact(artifact_zip, args.outdir)


if __name__ == "__main__":
    main()
