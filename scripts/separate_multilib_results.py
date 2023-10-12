import argparse
import os
from collections import defaultdict
from typing import Dict, List, Set
import sys

def parse_arguments():
    parser = argparse.ArgumentParser(description="Testsuite Compare Options")
    parser.add_argument(
        "-file",
        "--file-name",
        metavar="<string>",
        type=str,
        help="Path to file",
    )
    parser.add_argument(
        "-indir",
        "--directory-name",
        metavar="<string>",
        type=str,
        help="Path to file",
    )
    parser.add_argument(
        "-outdir",
        default="./",
        metavar="<string>",
        type=str,
        help="output directory",
    )
    return parser.parse_args()


def parse_file(file_name: str):
    target_info = defaultdict(list)
    with open(file_name, "r") as f:
        cur_target = None
        while True:
            line = f.readline()
            if line == "\n":
                break
            if "===" in line and "Unexpected fails for" in line:
                comps = line.strip().split(" ")
                cur_target = f"{comps[5]} {comps[6]}"
            target_info[cur_target].append(line)
        summary = f.readline() + f.readline() + f.readline()
        for target in target_info.keys():
            target_info[target].append("\n" + summary)
        while True:
            line = f.readline()
            if not line:
                break
            temp = line.split("|")[0].strip().split("/")
            comps = [i.strip() for i in temp]
            target = " ".join(comps[0:2])
            target_info[target].append(line)
                
    return target_info

def write_file(file_name: str, outdir: str, indir: str = "./"):
    targets = parse_file(os.path.join(indir, file_name))
    libc = "linux" if "linux" in file_name else "newlib"
    gcchash = file_name.split("-")[4]
    print(targets.keys())
    for target, content in targets.items():
        arch, abi = target.split(" ")
        fname = f"gcc-{libc}-{arch}-{abi}-{gcchash}-multilib-report.log"
        with open(f"{os.path.join(outdir, fname)}", "w") as f:
            f.writelines(content)

def main():
    args = parse_arguments()
    assert(args.directory_name is not None or args.file_name is not None)
    if args.directory_name is not None:
        for file in os.listdir(args.directory_name):
            if "non-multilib" in file:
                continue
            write_file(file, args.outdir, args.directory_name)
    if args.file_name is not None:
        write_file(args.file_name, args.outdir)
    
if __name__ == "__main__":
    main()
    
