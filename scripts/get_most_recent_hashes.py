# Gets the 100 most recent or subsequent hashes.

import os
import argparse


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Get closest valid GCC hash")
    parser.add_argument(
        "-hash",
        required=True,
        type=str,
        help="Commit hash of GCC to get artifacts for",
    )
    parser.add_argument(
        "-subsequent",
        action="store_true",
        help="Get the subsequent closest commit. Defaults to prior.",
    )
    return parser.parse_args()


def gcc_hashes(git_hash: str, subsequent: bool):
    """Get the most recent GCC hashes within a 100 commits (in order from closest to furthest)"""
    if subsequent is False:  # Get prior commit
        old_commit = (
            os.popen(
                f"cd gcc && git checkout master --quiet && git pull --quiet && git rev-parse {git_hash}~100"
            )
            .read()
            .strip()
        )
        print(f"git rev-list --ancestry-path {old_commit}~1..{git_hash}~1")
        commits = os.popen(
            f"cd gcc && git rev-list --ancestry-path {old_commit}^..{git_hash}^"
        ).read()
        commits = commits.splitlines()
    else:
        os.popen("cd gcc && git checkout master --quiet && git pull --quiet").read()
        commits = os.popen(
            f"cd gcc && git rev-list --ancestry-path {git_hash}..HEAD | head -100"
        ).read()
        commits = list(reversed(commits.splitlines()))

    return commits


def main(git_hash: str, subsequent: bool):
    commits = gcc_hashes(git_hash, subsequent)
    print(commits)


if __name__ == "__main__":
    args = parse_arguments()
    main(args.hash, args.subsequent)
