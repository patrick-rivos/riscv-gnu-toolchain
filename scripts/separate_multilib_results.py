import argparse
import os
from collections import defaultdict
from typing import Dict, List, Set
import sys

nicknames = {
    "--param=riscv-autovec-preference=": "autovec-",
    "--param=riscv-autovec-lmul=": "lmul-",
}

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
    print(f"parsing file: {file_name}")
    target_info = defaultdict(list)
    with open(file_name, "r") as f:
        cur_target = None
        while True:
            line = f.readline()
            if line == "\n":
                break
            if "===" in line and "Unexpected fails for" in line:
                comps = line.strip().split(" ")
                cur_target = f"{' '.join(comps[5:-1])}".strip()
            target_info[cur_target].append(line)
        summary = f.readline() + f.readline() + f.readline()
        for target in target_info.keys():
            target_info[target].append("\n" + summary)
        comps = None
        prev_line = None
        while True:
            line = f.readline()
            if not line:
                break
            if "/" not in line:
                comps += [line.strip()]
                target = " ".join(comps)
                target_info[target].append(prev_line)
                target_info[target].append(line)
            prev_line = line
            temp = line.split("|")[0].strip().split("/")
            comps = [i.strip() for i in temp]
            target = " ".join(comps)
            print(target, target_info.keys())
            if target in target_info.keys():
                target_info[target].append(line)

                
    return target_info

def write_file(file_name: str, outdir: str, multilib: str, indir: str = "./"):
    targets = parse_file(os.path.join(indir, file_name))
    libc = "linux" if "linux" in file_name else "newlib"
    gcchash = file_name.split("-")[4]
    print(targets.keys())

    # need to remove file name otherwise the previous file may be used in 
    # comparisons when we don't want it to
    # i.e. rv64gcv report log with only rv64gcv --param=riscv-autovec-preference=scalable
    # should only generate rv64gcv autovect scalable file and the original
    # rv64gcv file should not exist.
    print(f"attempting to remove original file: {os.path.join(indir, file_name)}")
    if (os.path.exists(os.path.join(indir, file_name))):
        print(f"file {os.path.join(indir, file_name)} removed")
        os.remove(os.path.join(indir, file_name))
    
    for target, content in targets.items():
        comps = target.split(" ")
        arch = comps[0]
        abi = comps[1]
        other_args = "_".join(comps[3:]) if len(comps) > 3 else None
        fname = None
        if other_args:
            for k,v in nicknames.items():
                other_args = other_args.replace(k, v)
            fname = f"gcc-{libc}-{arch}-{abi}-{gcchash}-{other_args}-{multilib}-report.log"
        else:
            fname = f"gcc-{libc}-{arch}-{abi}-{gcchash}-{multilib}-report.log"

        with open(f"{os.path.join(outdir, fname)}", "w") as f:
            f.writelines(content)

def main():
    args = parse_arguments()
    assert(args.directory_name is not None or args.file_name is not None)
    # Currently all precommit uses self-hosted runners all running multilib builds
    # Postfix everything to multilib for matching purposes
    multilib = "multilib"
    if args.directory_name is not None:
        for file in os.listdir(args.directory_name):
            if "failed" in file: # failed_build.txt failed_testsuite.txt
                continue
            write_file(file, args.outdir, multilib, args.directory_name)
    if args.file_name is not None:
        write_file(args.file_name, args.outdir, multilib)
    
if __name__ == "__main__":
    main()
    
