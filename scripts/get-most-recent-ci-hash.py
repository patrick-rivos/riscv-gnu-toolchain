# Gets the most recent hash that has an associated CI run

import os
import argparse
from typing import List
from github import Auth, Github

def gcc_hashes(hash: str, prior: bool):
    """ Get the most recent GCC hashes within a 100 commits (in order from closest to furthest)"""
    assert prior is True
    old_commit = os.popen(f'cd gcc && git checkout master --quiet && git pull --quiet && git rev-parse {hash}~100').read().strip()
    print(f'git rev-list --format=short --ancestry-path {old_commit}~1..{hash}~1')
    commits = os.popen(f'cd gcc && git rev-list --ancestry-path {old_commit}^..{hash}^').read()

    print(commits)

    return commits

def get_valid_hash(hashes: List[str], token: str):
    auth = Auth.Token(token)
    g = Github(auth=auth)

    repo = g.get_repo('patrick-rivos/riscv-gnu-toolchain')

    for hash in hashes:
        artifact_name = f'gcc-newlib-rv32gc-ilp32d-{hash}-non-multilib-report.log'
        artifacts = repo.get_artifacts(artifact_name).get_page(0)
        if len(artifacts) != 0:
            return hash

    return "No valid hash"

def main(hash: str, prior: bool, token: str):
    commits = gcc_hashes(hash, prior)
    commits = commits.splitlines()
    print(get_valid_hash(commits, token))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get closest valid GCC hash")
    parser.add_argument(
        "-hash",
        required=True,
        type=str,
        help="Commit hash of GCC to get artifacts for",
    )
    parser.add_argument(
        "-token",
        required=True,
        type=str,
        help="Github access token.",
    )
    parser.add_argument(
        "-prior",
        required=False,
        default=True,
        type=bool,
        help="Get the prior (or subsequent) closest commit. Defaults to prior.",
    )
    args = parser.parse_args()

    main(args.hash, args.prior, args.token)
