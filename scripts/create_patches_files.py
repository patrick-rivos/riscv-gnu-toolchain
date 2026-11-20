"""Create a series of files listing patches to apply (pre-reqs + interesting patch) for a given time period"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Any

import requests

from riscv_patch_scope import API, GCC_PROJECT, is_gcc_riscv_patch, patch_detail


def has_rise_check(checks: List[Dict[str, Any]]) -> bool:
    """Only our own checks suppress requeueing the overlap window.

    A pending check means this service already started the patch. Shadow runs
    without an account configured do not trust checks from another service.
    """
    username = os.environ.get("PATCHWORK_CHECK_USERNAME", "").strip()
    return bool(username) and any(
        check.get("user", {}).get("username") == username
        and check.get("context", "").startswith("toolchain-ci-rise-")
        for check in checks
    )


def parse_arguments():
    parser = argparse.ArgumentParser(description="Create Patch Files")
    parser.add_argument(
        "-start",
        "--start",
        metavar="<string>",
        type=str,
        help="Start timestamp for patches",
    )
    parser.add_argument(
        "-end",
        "--end",
        metavar="<string>",
        type=str,
        help="End timestamp for patches",
    )
    parser.add_argument(
        "-backup",
        "--backup",
        metavar="<string>",
        type=str,
        help="Previous end timestamp for patches",
    )
    parser.add_argument(
        "-patch",
        "--patch-id",
        metavar="<string>",
        type=str,
        help="Patch id to download",
    )
    parser.add_argument(
        "-file",
        "--patches-file",
        metavar="<file_path>",
        type=str,
        help="File of patch numbers to download",
    )
    parser.add_argument(
        "-project",
        "--project",
        metavar="<int>",
        type=int,
        default=GCC_PROJECT,
        choices=[GCC_PROJECT],
        help="Project number to pull from",
    )
    args = parser.parse_args()
    if args.patch_id is None and args.patches_file is None:
        if not all((args.backup, args.start, args.end)):
            parser.error(
                "provide -patch, -file, or a complete -backup/-start/-end window"
            )
    return args


def request_page(url, params=None):
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    return response


def window_patches(start, end):
    url = f"{API}/patches/"
    params = {
        "order": "date",
        "project": GCC_PROJECT,
        "since": start,
        "before": end,
        "per_page": 100,
    }
    while url:
        response = request_page(url, params)
        yield from response.json()
        url = response.links.get("next", {}).get("url")
        params = None


def selected_patches(current, overlap=()):
    """Current-window candidates plus older candidates that CI missed."""
    seen = set()
    for patches, check_overlap in ((current, False), (overlap, True)):
        for patch in patches:
            if patch["id"] in seen:
                continue
            seen.add(patch["id"])
            if not is_gcc_riscv_patch(patch):
                continue
            if check_overlap and has_rise_check(request_page(patch["checks"]).json()):
                continue
            yield patch


def write_patch_files(patches):
    urls = Path("patch_urls")
    metadata = Path("patchworks_metadata")
    urls.mkdir(exist_ok=True)
    metadata.mkdir(exist_ok=True)
    names = []
    series_cache = {}
    for patch in patches:
        # Ask Patchwork for the full ordered series, even when the polling
        # window starts halfway through it. Only the selected patch gets a job.
        if not patch.get("series"):
            raise ValueError(f"No series for Patchwork patch {patch['id']}")
        series_id = patch["series"][0]["id"]
        if series_id not in series_cache:
            series_cache[series_id] = request_page(f"{API}/series/{series_id}/").json()
        series = series_cache[series_id]
        prefix = []
        for member in series["patches"]:
            prefix.append(member["mbox"])
            if member["id"] == patch["id"]:
                break
        else:
            raise ValueError(f"Patch {patch['id']} is absent from series {series_id}")
        series_name = series["name"] or "unknown"
        series_name = "".join(
            c for c in series_name if c.isalnum() or c == " "
        ).replace(" ", "_")
        name = f"{series_id}-{series_name}-{len(prefix)}"
        names.append(name)
        (urls / name).write_text("".join(link + "\n" for link in prefix))
        (metadata / name).write_text(
            f"Applied patches: 1 -> {len(prefix)}\n"
            f"Associated series: {series['web_url']}\n"
            f"Last patch applied: {patch['web_url']}\n{patch['id']}"
        )
    Path("artifact_names.txt").write_text(json.dumps(names))


def main():
    args = parse_arguments()
    if args.patch_id is not None:
        patches = selected_patches([patch_detail(args.patch_id)])
    elif args.patches_file is not None:
        ids = Path(args.patches_file).read_text().split()
        patches = selected_patches(patch_detail(patch_id) for patch_id in ids)
    else:
        patches = selected_patches(
            window_patches(args.start, args.end),
            window_patches(args.backup, args.start),
        )
    write_patch_files(patches)


if __name__ == "__main__":
    main()
