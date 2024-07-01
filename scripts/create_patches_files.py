"""Create a series of files listing patches to apply (pre-reqs + interesting patch) for a given time period"""
import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Any, Tuple, Union
import requests

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
        default=6,
        help="Project number to pull from",
    )
    return parser.parse_args()


def create_files(series_name: Dict[str, str], series_url: Dict[str, str], download_links: Dict[str, List[List[str]]], outdir: str):
    # Create possible missing output file directory
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    artifact_names: List[str] = []
    for series_number, links_list in download_links.items():
        for links in links_list:
            fname = f"{series_number}-{series_name[series_number]}-{len(links)}"
            artifact_names.append(fname)
            with open(os.path.join(outdir, fname), "w") as f:
                if outdir == './patchworks_metadata':
                    _pname, url, pid = links[-1].split("\t")
                    f.write(f"Applied patches: 1 -> {len(links)}\n")
                    f.write(f"Associated series: {series_url[series_number]}\n")
                    f.write(f"Last patch applied: {url}\n")
                    f.write(f"{pid}")
                else:
                    f.writelines(links)

    with open("./artifact_names.txt", "w") as f:
        f.write(str(artifact_names))

def interesting_patch(patch: Dict[str, Any]):
    """Grep the patch mbox file for key terms/email addresses."""
    r = requests.get(patch["mbox"], timeout=300) # 5 minutes
    # https://stackoverflow.com/questions/44203397/python-requests-get-returns-improperly-decoded-text-instead-of-utf-8/52615216#52615216
    r.encoding = r.apparent_encoding
    patch_mbox = r.text.lower()

    # Search for riscv, risc-v, patchworks-ci@rivosinc.com
    # mbox is already lowercased
    return "riscv" in patch_mbox or "risc-v" in patch_mbox or  "patchworks-ci@rivosinc.com" in patch_mbox.lower()

def parse_patches(patches: List[Dict[str, Any]], patch_id: Union[None, str] = None):
    riscv_download_links: DefaultDict[str, List[List[str]]] = defaultdict(list)
    all_download_links: DefaultDict[str, List[List[str]]] = defaultdict(list)
    riscv_patchworks_links: DefaultDict[str, List[List[str]]]  = defaultdict(list)
    all_patchworks_links: DefaultDict[str, List[List[str]]]  = defaultdict(list)
    series_name: Dict[str, str] = {}
    series_url: Dict[str, str] = {}

    # Used for asserts
    riscv_title_patch_links: List[List[str]] = []
    riscv_title_patchworks_links: List[List[str]] = []

    for patch in patches:
        assert len(patch["series"]) == 1
        found_series = patch["series"][0]["id"]
        print(f"currently parsing:\n\t{patch['series'][0]}")

        if len(all_download_links[found_series]) == 0:
            all_download_links[found_series].append([patch["mbox"] + "\n"])
            all_patchworks_links[found_series].append([f"{patch['name']}\t{patch['web_url']}\t{patch['id']}\n"])
        else:
            prev_download_link = list(all_download_links[found_series][-1])
            prev_download_link.append(patch["mbox"] + "\n")
            all_download_links[found_series].append(prev_download_link)
            prev_patchworks_link = list(all_patchworks_links[found_series][-1])
            prev_patchworks_link.append(f"{patch['name']}\t{patch['web_url']}\t{patch['id']}\n")
            all_patchworks_links[found_series].append(prev_patchworks_link)

        if patch_id is None and interesting_patch(patch):
            print(f"Patch {patch['name']} is an interesting patch")
            riscv_download_links[found_series].append(all_download_links[found_series][-1])
            riscv_patchworks_links[found_series].append(all_patchworks_links[found_series][-1])

        # Old check, used for asserts
        if patch_id is None and ("risc-v" in patch["name"].lower() or "riscv" in patch["name"].lower()):
            riscv_title_patch_links.append(all_download_links[found_series][-1])
            riscv_title_patchworks_links.append(all_patchworks_links[found_series][-1])

        if patch_id is not None and patch["id"] == patch_id:
            print(f"Patch {patch['name']} is the specified patch")
            riscv_download_links[found_series].append(all_download_links[found_series][-1])
            riscv_patchworks_links[found_series].append(all_patchworks_links[found_series][-1])

        if found_series not in series_name:
            if patch["series"][0]["name"] is None:
                series_name[found_series] = "unknown"
            else:
                series_name[found_series] = "".join(letter for letter in patch["series"][0]["name"] if letter.isalnum() or letter == " ").replace(" ","_")
            series_url[found_series] = patch["series"][0]["web_url"]

    # flatten link values and assert the lists are the same
    download_links = list(riscv_download_links.values())
    download_links = [item for sublist in download_links for item in sublist]
    patchworks_links = list(riscv_patchworks_links.values())
    patchworks_links = [item for sublist in patchworks_links for item in sublist]

    for patch_links in riscv_title_patch_links:
        assert any(
            patch_links == links for links in download_links
        ), f"Expected match (risc-v/riscv in title): {patch_links} not in links: {download_links}"
    for patch_links in riscv_title_patchworks_links:
        assert any(
            patch_links == links for links in patchworks_links
        ), f"Expected match (risc-v/riscv in title): {patch_links} not in patchworks links: {patchworks_links}"

    return series_name, series_url, riscv_download_links, riscv_patchworks_links

def make_api_request(url: str):
    print(url)
    r = requests.get(url)
    print(r.status_code)
    patches = json.loads(r.text)
    return patches

def get_single_patch_info(url: str, patch_id: Union[str, None] = None):
    patches = make_api_request(url)

    # Check for dependencies
    patch_id = patches["id"]
    series_url = f"https://patchwork.sourceware.org/api/1.3/series/{patches['series'][0]['id']}"
    series_info = make_api_request(series_url)
    if series_info["received_total"] > 1:
        patch_ids = [patch['id'] for patch in series_info['patches']]
        patches = [make_api_request(f"https://patchwork.sourceware.org/api/1.3/patches/{pid}") for pid in patch_ids]
        return parse_patches(patches, patch_id)
    return parse_patches([patches], patch_id)

## Single patch ID

def get_single_patch(patch_id: str):
    url = f"https://patchwork.sourceware.org/api/1.3/patches/{patch_id}"

    series_name, series_url, download_links, patchwork_links = get_single_patch_info(url, patch_id)

    print("creating download links")
    create_files(series_name, series_url, download_links, "./patch_urls")
    print("creating patchworks links")
    create_files(series_name, series_url, patchwork_links, "./patchworks_metadata")

## File full of patch IDs

def get_patches_file(file_path: str):
    patch_nums = None
    with open(file_path, "r") as f:
        patch_nums = f.read().strip().split(" ")

    print(patch_nums)

    super_series_name: Dict[str, str] = {}
    super_series_url: Dict[str, str] = {}
    super_download_links: Dict[str, List[List[str]]] = {}
    super_patchwork_links: Dict[str, List[List[str]]] = {}
    for patch in patch_nums:
        url = f"https://patchwork.sourceware.org/api/1.3/patches/{patch}"
        series_name, series_url, download_links, patchwork_links = get_single_patch_info(url)
        super_series_name.update(series_name)
        super_series_url.update(series_url)
        super_download_links.update(download_links)
        super_patchwork_links.update(patchwork_links)

    print("creating download links")
    create_files(super_series_name, super_series_url, super_download_links, "./patch_urls")
    print("creating patchworks links")
    create_files(super_series_name, super_series_url, super_patchwork_links, "./patchworks_metadata")

def get_overlap_dict(download: Dict[str, List[List[str]]], early: Dict[str, List[List[str]]]):
    overlap = set(early.keys()).intersection(set(download.keys()))
    if len(overlap) != 0:
        print("found overlap, downloading sections")
        for series in overlap:
            download[series] = [list(early[series][-1]) + list(val) for val in download[series]]

    return download

def make_api_request_and_get_headers(url: str):
    print(url)
    r = requests.get(url)
    print(r.status_code)
    patches = json.loads(r.text)
    return r.headers, patches

def get_patch_info(url: str):
    patches: List[Dict[str, Any]] = []
    for page_num in range(1, 10):
        headers, page = make_api_request_and_get_headers(url + f"&page={page_num}")
        patches += page
        if 'rel="next"' not in headers['Link']:
            break

    return parse_patches(patches)

def get_multiple_patches(start: str, end: str, backup: str, project: int):
    """Get all patches within a timeframe"""
    url = "https://patchwork.sourceware.org/api/1.3/patches/?order=date&project={}&since={}&before={}"

    series_name, series_url, download_links, patchworks_links = get_patch_info(url.format(project, start, end))

    _early_series_name, _early_series_url, early_download_links, early_patchworks_links = get_patch_info(url.format(project, backup, start))

    print("creating download links")
    new_download_links = get_overlap_dict(download_links, early_download_links)
    create_files(series_name, series_url, new_download_links, "./patch_urls")
    print("creating patchworks links")
    new_patchworks_links = get_overlap_dict(patchworks_links, early_patchworks_links)
    create_files(series_name, series_url, new_patchworks_links, "./patchworks_metadata")

def main():
    args = parse_arguments()
    if args.patch_id is not None:
        get_single_patch(args.patch_id)
    elif args.patches_file is not None:
        get_patches_file(args.patches_file)
    else:
        print(f"project: {args.project}")
        get_multiple_patches(args.start, args.end, args.backup, args.project)

if __name__ == "__main__":
    main()
