"""Select GCC RISC-V patches from the Sourceware Patchwork API."""

import argparse
import re
import subprocess
import sys

import requests

API = "https://patchwork.sourceware.org/api/1.3"
GCC_PROJECT = 6
RISCV_TAG = r"risc-?v(?:32|64)?"
RISCV_SUBJECT = re.compile(rf"^(?:gcc\s*[:/]\s*)?{RISCV_TAG}(?=[:\s]|$)", re.IGNORECASE)
# Only target-specific directories in the GCC source tree. Changes to common
# files can still be selected by an explicit RISC-V subject.
TARGET_DIRS = (
    "gcc/config/riscv/",
    "gcc/common/config/riscv/",
    "gcc/testsuite/gcc.target/riscv/",
    "gcc/testsuite/g++.target/riscv/",
    "gcc/testsuite/gfortran.target/riscv/",
    "gcc/testsuite/rust.target/riscv/",
    "libgcc/config/riscv/",
    "libatomic/config/riscv/",
    "libffi/src/riscv/",
    "libgomp/config/linux/riscv/",
    "libgomp/testsuite/libgomp.target/riscv/",
    "libstdc++-v3/config/cpu/riscv/",
)


def has_target_subject(title):
    # Patchwork preserves bracketed tags such as [PATCH,RISC-V,v3].
    title = title.lstrip()
    while tag := re.match(r"^\[([^\]]*)\]\s*", title):
        for field in re.split(r"[,\s/:]+", tag[1]):
            if re.fullmatch(RISCV_TAG, field, re.IGNORECASE):
                return True
        title = title[tag.end() :]
    return bool(RISCV_SUBJECT.match(title))


def patch_detail(patch_id):
    response = requests.get(f"{API}/patches/{int(patch_id)}/", timeout=60)
    response.raise_for_status()
    return response.json()


def touches_target(diff):
    # Git parses the actual file headers, including quoted paths and renames.
    # --numstat never applies a patch. Reverse statistics cover renames out of
    # a target directory, where forward statistics only show the destination.
    for direction in ([], ["--reverse"]):
        result = subprocess.run(
            [
                "git",
                "apply",
                "--numstat",
                "-z",
                "-p0",
                "--allow-empty",
                *direction,
                "-",
            ],
            input=diff.encode(),
            capture_output=True,
            cwd="/",
        )
        if result.returncode:
            return False
        for record in result.stdout.split(b"\0"):
            if not record:
                continue
            path = record.split(b"\t", 2)[2].decode(errors="surrogateescape")
            if path.startswith(("a/", "b/")):
                path = path[2:]
            if ".." not in path.split("/") and path.startswith(TARGET_DIRS):
                return True
    return False


def is_gcc_riscv_patch(patch):
    if (patch.get("project") or {}).get("id") != GCC_PROJECT:
        return False
    if has_target_subject(patch["name"]):
        return True
    # Patchwork list responses omit the diff. The detail serializer provides
    # it separately from sender headers, commit messages and discussion.
    if "diff" not in patch:
        patch = patch_detail(patch["id"])
        if (patch.get("project") or {}).get("id") != GCC_PROJECT:
            return False
    return bool(patch.get("diff")) and touches_target(patch["diff"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patch_id", type=int)
    args = parser.parse_args()
    if is_gcc_riscv_patch(patch_detail(args.patch_id)):
        return 0
    print(f"Patch {args.patch_id} is outside the GCC RISC-V CI scope", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
