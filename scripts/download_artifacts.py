import argparse
import os
import re
from typing import List, Tuple
from github import Auth, Github
from download_artifact import download_artifact, extract_artifact, search_for_artifact


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Download valid log artifacts")
    parser.add_argument(
        "-hash",
        required=True,
        type=str,
        help="Commit hash of GCC to get artifacts for",
    )
    parser.add_argument(
        "-phash",
        required=False,
        type=str,
        help="Previous commit hash if exists",
    )
    parser.add_argument(
        "-repo",
        required=True,
        type=str,
        help="Name of the repo to download from",
    )
    parser.add_argument(
        "-token",
        required=True,
        type=str,
        help="Github access token",
    )
    return parser.parse_args()


def get_valid_artifact_hash(
    hashes: List[str], repo_name: str, token: str, artifact_name: str
) -> Tuple[str, "str | None"]:
    """
    Searches for the most recent GCC hash that has the artifact specified by
    @param artifact_name. Also returns id of found artifact for download.
    """
    # Authenticate ahead of time so we don't repeatedly authenticate for each of
    # the requests.
    auth = Auth.Token(token)
    github = Github(auth=auth)

    for git_hash in hashes:
        artifact_id = search_for_artifact(
            artifact_name.format(git_hash), repo_name, token, github
        )

        if artifact_id is not None:
            return git_hash, artifact_id

    return "No valid hash", None


def get_possible_artifact_names() -> List[str]:
    """
    Generates all possible permutations of target artifact logs and
    removes unsupported targets

    Current Support:
      Linux: rv32/64 multilib non-multilib
      Newlib: rv32/64 non-multilib
      Arch extensions: gc
    """
    libc = ["gcc-linux", "gcc-newlib"]
    arch = ["rv32{}-ilp32d-{}", "rv64{}-lp64d-{}"]
    multilib = ["multilib", "non-multilib"]

    arch_extensions = [
        "gc",
        "gcv",
        "gc_zba_zbb_zbc_zbs",
        "gcv_zvbb_zvbc_zvkg_zvkn_zvknc_zvkned_zvkng_zvknha_zvknhb_zvks_zvksc_zvksed_zvksg_zvksh_zvkt",
        "imafdcv_zicond_zawrs_zbc_zvkng_zvksg_zvbb_zvbc_zicsr_zba_zbb_zbs_zicbom_zicbop_zicboz_zfhmin_zkt",
    ]

    all_lists = [
        "-".join([i, j, k])
        for i in libc
        for j in arch
        for k in multilib
        if not ("rv32" in j and k == "multilib")
    ]

    all_names = [
        name.format(ext, "{}")
        for name in all_lists
        for ext in arch_extensions
        if not ("gcv" in ext and "non-multilib" not in name)
        and not ("gc_" in ext and "non-multilib" not in name)
        and not ("imafdcv_" in ext and "non-multilib" not in name)
        and not (
            "rv32" in name
            and "imafdcv_zicond_zawrs_zbc_zvkng_zvksg_zvbb_zvbc_zicsr_zba_zbb_zbs_zicbom_zicbop_zicboz_zfhmin_zkt"
            in ext
        )
        and not ("non-multilib" in name and ext == "gc")
    ]
    return all_names


def artifact_exists(artifact_name: str) -> bool:
    """
    @param artifact_name is the artifact associated with build success
    If the artifact does not exist, something failed and logs error into
    appropriate file
    """
    build_name = f"{artifact_name}.zip"
    log_name = f"{artifact_name}-report.log"
    build_failed = False
    # check if the build failed
    if not os.path.exists(os.path.join("./temp", build_name)) and not os.path.exists(
        os.path.join("./current_logs", log_name)
    ):
        print(f"build failed for {artifact_name}")
        build_failed = True
        with open("./current_logs/failed_build.txt", "a+", encoding="UTF8") as f:
            f.write(f"{artifact_name}|Check logs\n")

    # check if the testsuite failed
    if not os.path.exists(os.path.join("./current_logs", log_name)):
        print(f"testsuite failed for {artifact_name}")
        if not build_failed:
            with open(
                "./current_logs/failed_testsuite.txt", "a+", encoding="UTF8"
            ) as f:
                f.write(
                    f"{artifact_name}|Cannot find testsuite artifact. Likely caused by testsuite timeout.\n"
                )
        return False
    return True


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


def download_all_artifacts(
    current_hash: str, previous_hash: str, repo_name: str, token: str
):
    """
    Goes through all possible artifact targets and downloads it
    if it exists. Downloads previous successful hash's artifact
    as well. Runs comparison on the downloaded artifacts
    """

    prev_commits = gcc_hashes(current_hash, False)
    artifact_name_templates = get_possible_artifact_names()
    # TODO: Refactor this block
    for artifact_name_template in artifact_name_templates:
        artifact = artifact_name_template.format(current_hash)
        if not artifact_exists(artifact):
            continue

        artifact_name_template += "-report.log"

        # check if we already have a previous artifact available
        # mostly for regenerate issues
        if previous_hash:
            name_components = artifact_name_template.split("-")
            name_components[4] = "{}"
            previous_name = "-".join(name_components).format(previous_hash)
            name_components[4] = "[^-]*"
            name_regex = "-".join(name_components)
            dir_contents = " ".join(os.listdir("./previous_logs"))
            possible_previous_logs = re.findall(name_regex, dir_contents)
            if len(possible_previous_logs) > 1:
                print(
                    f"found more than 1 previous log for {name_regex}: {possible_previous_logs}"
                )
                for log in possible_previous_logs:  # remove non-recent logs
                    if previous_name not in log:
                        print(f"removing {log} from previous_logs")
                        os.remove(os.path.join("./previous_logs", log))
                continue
            if len(possible_previous_logs) == 1:
                print(
                    f"found single log: {possible_previous_logs[0]}. Skipping download"
                )
                continue

        # download previous artifact
        base_hash, base_id = get_valid_artifact_hash(
            prev_commits, repo_name, token, artifact_name_template
        )
        if base_hash != "No valid hash":
            artifact_zip = download_artifact(
                artifact_name_template.format(base_hash), str(base_id), token
            )
            extract_artifact(
                artifact_name_template.format(base_hash),
                artifact_zip,
                outdir="previous_logs",
            )
        else:
            print(
                f"found no valid hash for {artifact_name_template}. possible hashes: {prev_commits}"
            )


def main():
    args = parse_arguments()
    download_all_artifacts(args.hash, args.phash, args.repo, args.token)


if __name__ == "__main__":
    main()
