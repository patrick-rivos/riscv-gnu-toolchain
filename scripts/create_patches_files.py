import argparse
import requests
import json
import os
from collections import defaultdict
from typing import Dict, List, Set

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

def parse_patches(patches, outdir="./patch_urls"):
    download_links: defaultdict[str, List[str]] = defaultdict(list)
    patchworks_links: defaultdict[str, List[str]]  = defaultdict(list)
    series_name = {}
    series_url = {}
    for patch in patches:
        assert len(patch["series"]) == 1
        found_series = patch["series"][0]["id"]
        print(f"currently parsing:\n\t{patch['series'][0]}")
        if len(download_links[found_series]) == 0:
            download_links[found_series].append([patch["mbox"] + "\n"])
            patchworks_links[found_series].append([f"{patch['name']}\t{patch['web_url']}\t{patch['id']}\n"])
        else:
            prev_download_link = list(download_links[found_series][-1])
            prev_download_link.append(patch["mbox"] + "\n")
            download_links[found_series].append(prev_download_link)
            prev_patchworks_link = list(patchworks_links[found_series][-1])
            prev_patchworks_link.append(f"{patch['name']}\t{patch['web_url']}\t{patch['id']}\n")
            patchworks_links[found_series].append(prev_patchworks_link)
        if found_series not in series_name:
            if patch["series"][0]["name"] is None:
                series_name[found_series] = "unknown"
            else:
                series_name[found_series] = "".join(letter for letter in patch["series"][0]["name"] if letter.isalnum() or letter == " ").replace(" ","_")
            series_url[found_series] = patch["series"][0]["web_url"]

    return series_name, series_url, download_links, patchworks_links


def create_files(series_name: Dict[str, str], series_url: Dict[str, str], download_links: Dict[str, List[List[str]]], outdir: str):
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

def get_overlap_dict(download: Dict[str, List[str]], early: Dict[str, List[str]]):
    overlap = set(early.keys()).intersection(set(download.keys()))
    if len(overlap) != 0:
        print("found overlap, downloading sections")
        for series in overlap:
            download[series] = [list(early[series][-1]) + list(val) for val in download[series]]

    return download

def make_api_request(url):
    print(url)
    r = requests.get(url)
    print(r.status_code)
    patches = json.loads(r.text)
    return patches

def get_patch_info(url):
    patches = make_api_request(url)
    if isinstance(patches, list):
        return parse_patches(patches)
    else:
        # Getting a single patch back from the API means we were invoked with a particular patch id, not a time range.
        patch_id = patches["id"]
        series_url = f"https://patchwork.sourceware.org/api/1.3/series/{patches['series'][0]['id']}"
        series_info = make_api_request(series_url)
        if series_info["received_total"] > 1:
            patch_ids = [patch['id'] for patch in series_info['patches'] if patch['id'] <= patch_id]
            patches = [make_api_request(f"https://patchwork.sourceware.org/api/1.3/patches/{pid}") for pid in patch_ids]
            return parse_patches(patches)
        return parse_patches([patches])

def get_single_patch(patch: str):
    url = f"https://patchwork.sourceware.org/api/1.3/patches/{patch}"

    series_name, series_url, download_links, patchwork_links = get_patch_info(url)

    print("creating download links")
    create_files(series_name, series_url, download_links, "./patch_urls")
    print("creating patchworks links")
    create_files(series_name, series_url, patchwork_links, "./patchworks_metadata")

def get_patches_file(file_path: str):
    patch_nums = None
    with open(file_path, "r") as f:
        patch_nums = f.read().strip().split(" ")

    print(patch_nums)

    super_series_name = {}
    super_series_url = {}
    super_download_links = {} 
    super_patchwork_links = {}
    for patch in patch_nums:
        url = f"https://patchwork.sourceware.org/api/1.3/patches/{patch}"
        series_name, series_url, download_links, patchwork_links = get_patch_info(url)
        super_series_name.update(series_name)
        super_series_url.update(series_url)
        super_download_links.update(download_links)
        super_patchwork_links.update(patchwork_links)

    print("creating download links")
    create_files(super_series_name, super_series_url, super_download_links, "./patch_urls")
    print("creating patchworks links")
    create_files(super_series_name, super_series_url, super_patchwork_links, "./patchworks_metadata")

def get_multiple_patches(start: str, end: str, backup: str, project: int):
    if project == 6: #GCC
        url = "https://patchwork.sourceware.org/api/1.3/patches/?order=date&q=RISC-V&project={}&since={}&before={}"
    else: # glibc
        url = "https://patchwork.sourceware.org/api/1.3/patches/?order=date&q=riscv&project={}&since={}&before={}"

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
