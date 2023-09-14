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
        required=True,
        type=str,
        help="Start timestamp for patches",
    )
    parser.add_argument(
        "-end",
        "--end",
        metavar="<string>",
        required=True,
        type=str,
        help="End timestamp for patches",
    )
    parser.add_argument(
        "-backup",
        "--backup",
        metavar="<string>",
        required=True,
        type=str,
        help="Previous end timestamp for patches",
    )
    return parser.parse_args()

def parse_patches(patches, outdir="./patch_urls"):
    download_links = defaultdict(list)
    series_name = {}
    for patch in patches:
        assert len(patch["series"]) == 1
        found_series = patch["series"][0]["id"]
        if len(download_links[found_series]) == 0:
            download_links[found_series].append([patch["mbox"] + "\n"])
        else:
            prev_links = list(download_links[found_series][-1])
            prev_links.append(patch["mbox"] + "\n")
            download_links[found_series].append(prev_links)
        if found_series not in series_name:
            series_name[found_series] = "".join(letter for letter in patch["series"][0]["name"] if letter.isalnum() or letter == " ").replace(" ","_")

    return series_name, download_links


def create_files(series_name: Dict[str, List[str]], download_links: Dict[str, List[List[str]]], outdir="./patch_urls"):
    artifact_names = []
    for series_number, links_list in download_links.items():
        for links in links_list:
            fname = f"{series_number}-{series_name[series_number]}-{len(links)}"
            artifact_names.append(fname)
            with open(os.path.join(outdir, fname), "w") as f:
                f.writelines(links)

    with open("./artifact_names.txt", "w") as f:
        f.write(str(artifact_names))

def get_patches(start: str, end: str, backup: str):
    url = "https://patchwork.sourceware.org/api/1.3/patches/?order=date&q=RISC-V&project=6&since={}&before={}"

    print(url.format(start, end))
    r = requests.get(url.format(start, end))
    patches = json.loads(r.text)
    series_name, download_links = parse_patches(patches)

    print(url.format(backup, start))
    r = requests.get(url.format(backup, start))
    patches = json.loads(r.text)
    early_series_name, early_download_links = parse_patches(patches)

    overlap = set(early_download_links.keys()).intersection(set(download_links.keys()))

    if len(overlap) == 0:
        print("no overlap. creating as usual")
        create_files(series_name, download_links)
    else:
        print("overlap, downloading sections")
        for series in overlap:
            download_links[series] = [list(early_download_links[series][-1]) + list(val) for val in download_links[series]]
        create_files(series_name, download_links)

def main():
    args = parse_arguments()
    get_patches(args.start, args.end, args.backup)

if __name__ == "__main__":
    main()
