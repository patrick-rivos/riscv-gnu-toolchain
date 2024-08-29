import argparse
import json
import requests
import os
import re
from typing import List, Tuple
from pathlib import Path
from github import Auth, Github
from tempfile import TemporaryDirectory
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
    parser.add_argument(
        "-prefix",
        required=False,
        default="",
        type=str,
        help="Artifact prefix",
    )
    parser.add_argument(
        "-build-logs",
        action="store_true",
        help="If specified, also download the build log artifacts",
    )
    parser.add_argument(
        "-build-logs-dir", required=False, type=str, default="previous_build_logs"
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


def get_weekly_names(prefix: str) -> List[str]:
    """
    Generates all permutaions of target artifact logs for
    weekly runners

    Current Weekly Builds (prefixes):
    zve_
    rvx_zvl_
    rvx_zvl_lmulx_
    checking_
    """

    if prefix == "checking_":
        return ["checking_gcc-linux-rv64gcv_zicond-lp64d-{}-multilib"]

    # don't test newlib with weekly runs
    libc = [f"{prefix}gcc-linux"]
    arch = ["rv32{}-ilp32d-{}", "rv64{}-lp64d-{}"]

    possible_arch_extensions = [
        "gcv_zve64d",
        "gcv_zvl1024b",
        "gcv_zvl512b",
        "gcv_zvl256b",
        "gcv_zvl128b",
    ]
    # each extension ends in '_'. Use this since lmul extensions
    # use the same arch extension but the prefix is
    # currently structured as rvx_zvl_lmulx_
    is_lmul_prefix = "lmul" in prefix
    comps = prefix.split("_")
    prefix_arch = ""

    if len(comps) == 2:
        prefix = comps[0]
    else:
        prefix = comps[1]
        prefix_arch = comps[0]

    if is_lmul_prefix:
        multilib_arch_extensions = [
            ext for ext in possible_arch_extensions if prefix in ext
        ]
    else:
        # Non lmul zvl runs do not run 128 since that's the default and is
        # caught by the run-frequent runs. However, it would cause a false
        # build-failure on the zvl runs because it can't find the gcv_zvl128b
        # binary
        multilib_arch_extensions = [
            ext
            for ext in possible_arch_extensions
            if prefix in ext and "128" not in ext
        ]
    print("prefix arch:", prefix_arch)

    # now have weekly runners rv32 zvl multilib variants
    multilib_lists = ["-".join([i, j, "multilib"]) for i in libc for j in arch]
    if prefix_arch != "":
        multilib_lists = [
            name for name in multilib_lists if prefix_arch in name.split("-")[2]
        ]

    multilib_names = [
        name.format(ext, "{}")
        for name in multilib_lists
        for ext in multilib_arch_extensions
    ]

    return multilib_names


def get_binutils_names(prefix: str) -> List[str]:
    """
    Generates all permutaions of target artifact logs for
    binutils runs
    """
    assert prefix == "binutils_"

    multilib_names = [
        "binutils_gcc-linux-rv64gc-lp64d-{}-multilib",
        "binutils_gcc-linux-rv32gc-ilp32d-{}-multilib",
        "binutils_gcc-newlib-rv64gc-lp64d-{}-multilib",
        "binutils_gcc-newlib-rv32gc-ilp32d-{}-multilib",
    ]

    return multilib_names


def get_frequent_names(prefix: str) -> List[str]:
    """
    Generates all permutaions of target artifact logs for
    build frequent runners
    """
    libc = [f"{prefix}gcc-linux", f"{prefix}gcc-newlib"]
    arch = ["rv32{}-ilp32d-{}", "rv64{}-lp64d-{}"]

    multilib_arch_extensions = [
        "gcv",
        "imc",
        "imc_zba_zbb_zbc_zbs",
    ]

    multilib_lists = [
        "-".join([i, j, "multilib"]) for i in libc for j in arch if "rv64" in j
    ]

    multilib_names = [
        name.format(ext, "{}")
        for name in multilib_lists
        for ext in multilib_arch_extensions
        if not ("linux" in name and "imc" in ext)  # only test uc on newlib
    ]

    non_multilib_arch_extensions = [
        "gc",
        "gc_zba_zbb_zbc_zbs",
    ]

    non_multilib_lists = ["-".join([i, j, "non-multilib"]) for i in libc for j in arch]

    non_multilib_names = [
        name.format(ext, "{}")
        for name in non_multilib_lists
        for ext in non_multilib_arch_extensions
    ]

    return multilib_names + non_multilib_names


def get_possible_artifact_names(prefix: str) -> List[str]:
    """
    Generates all possible permutations of target artifact logs and
    removes unsupported targets

    Current Support:
      Linux: rv32/64 multilib non-multilib
      Newlib: rv32/64 non-multilib
      Arch extensions: gc
    """
    # Weekly arch extensions included since rv64gcv_zv* doesn't
    # exist without a prefix
    if prefix == "" or prefix == "coord_":
        return get_frequent_names(prefix)
    elif prefix == "binutils_":
        return get_binutils_names(prefix)
    else:
        return get_weekly_names(prefix)


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


def gcc_hashes(git_hash: str, issue_hashes: List[str], project: str):
    """Sort the given issue hashes from closest to furthest."""
    old_commit = (
        os.popen(
            f"cd {project} && git checkout master --quiet && git pull --quiet && git rev-parse {git_hash}~10000"
        )
        .read()
        .strip()
    )
    print(f"git rev-list --topo-order {old_commit}..{git_hash}~1")
    commits = os.popen(
        f"cd {project} && git rev-list --topo-order {old_commit}..{git_hash}~1"
    ).read()
    commits = commits.splitlines()
    sorted_issue_hashes = [commit for commit in commits if commit in issue_hashes]

    return sorted_issue_hashes


def issue_hashes(repo_name: str, token: str):
    params = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {token}",
        "X-Github-Api-Version": "2022-11-28",
    }
    response = requests.get(
        f"https://api.github.com/repos/{repo_name}/issues?page=1&per_page=100&state=all",
        headers=params,
        timeout=15 * 60,  # 15 min timeout
    )
    print(f"getting most recent 100 issues: {response.status_code}")
    issues = json.loads(response.text)
    hashes = [
        issue["title"].split(" ")[-1]
        for issue in issues
        if "pull_request" not in issue.keys()
    ]
    return hashes


def search_and_download_previous_report_artifact(
    artifact_name_template: str,
    previous_hash: str,
    prev_commits: List[str],
    repo_name: str,
    token: str,
):
    """Download a most recent previous report artifact and return the corresponding hash.
    Return None if no corresponding hash has been found
    """
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
            return previous_hash
        if len(possible_previous_logs) == 1:
            print(f"found single log: {possible_previous_logs[0]}. Skipping download")
            return previous_hash

    # download previous artifact
    base_hash, base_id = get_valid_artifact_hash(
        prev_commits, repo_name, token, artifact_name_template
    )
    if base_hash != "No valid hash":
        artifact_zip = download_artifact(
            artifact_name_template.format(base_hash),
            str(base_id),
            token,
            repo_name,
            "./temp/",
        )
        extract_artifact(
            artifact_zip,
            outdir="previous_logs",
        )
        return base_hash

    print(
        f"found no valid hash for {artifact_name_template}. possible hashes: {prev_commits}"
    )
    return None


def download_build_log_artifact(
    artifact_name_template: str,
    base_hash: str,
    repo_name: str,
    token: str,
    output_dir: str,
):
    """Download the build log zipfiles for a corresponding base_hash and extract them to output_dir"""
    # input validation
    if not base_hash:
        print("Missing base hash, skipping downloading the build log artifact")
        return

    target_format_pat = re.compile(r"gcc-")
    BUILD_LOG_SUFFIX = "-build-log"
    # Remove the starting gcc- and concatenate with the suffix
    artifact_name = target_format_pat.sub(
        "", artifact_name_template.format(base_hash) + BUILD_LOG_SUFFIX
    )

    # Check if the artifact name exists inside the output directory
    previous_build_log_path = Path(f"./{output_dir}/{artifact_name}")
    if previous_build_log_path.exists():
        # Remove this line and uncomment the print, return line if build log artifact is downloaded more than once in the future. https://github.com/patrick-rivos/riscv-gnu-toolchain/pull/526#discussion_r1647981167
        raise RuntimeError("Build log artifact is currently downloaded only once.")
        # print(f"This artifact already exists in {previous_build_log_path}. Skip download.")
        # return

    # Search for the artifact id
    auth = Auth.Token(token)
    github = Github(auth=auth)
    artifact_id = search_for_artifact(artifact_name, repo_name, token, github)
    if not artifact_id:
        print(f"{artifact_name} doesn't exist in {repo_name}")
        return

    # download the zip file in a temporary directory to minimize side effect
    with TemporaryDirectory() as tmp_dir:
        artifact_zip = download_artifact(
            artifact_name, artifact_id, token, repo_name, tmp_dir
        )
        extract_artifact(
            artifact_zip,
            outdir=output_dir,
        )


def download_all_artifacts(
    current_hash: str,
    previous_hash: str,
    repo_name: str,
    token: str,
    prefix: str,
    build_logs: bool,
    build_logs_dir: str,
):
    """
    Goes through all possible artifact targets and downloads it
    if it exists. Downloads previous successful hash's artifact
    as well. Runs comparison on the downloaded artifacts
    """

    # get hashes from the most recent 100 issues
    issue_commits = issue_hashes(repo_name, token)

    # sort most recent issue commit hashes by topological order
    prev_commits = gcc_hashes(
        current_hash, issue_commits, "binutils" if prefix == "binutils_" else "gcc"
    )

    artifact_name_templates = get_possible_artifact_names(prefix)
    print(artifact_name_templates)

    for artifact_name_template in artifact_name_templates:
        artifact = artifact_name_template.format(current_hash)
        # If this target failed to generate an artifact, skip
        if not artifact_exists(artifact):
            continue

        # Download all the required artifacts
        base_hash = search_and_download_previous_report_artifact(
            artifact_name_template, previous_hash, prev_commits, repo_name, token
        )
        if build_logs:
            download_build_log_artifact(
                artifact_name_template, base_hash, repo_name, token, build_logs_dir
            )


def main():
    args = parse_arguments()
    download_all_artifacts(
        args.hash,
        args.phash,
        args.repo,
        args.token,
        args.prefix,
        args.build_logs,
        args.build_logs_dir,
    )


if __name__ == "__main__":
    main()
