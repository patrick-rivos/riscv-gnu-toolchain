import argparse

def parse_arguments():
    parser = argparse.ArgumentParser(description="Create Patch Files")
    parser.add_argument(
        "-linter-log",
        "--linter-log",
        metavar="<file>",
        required=True,
        type=str,
        help="Linter log file",
    )
    parser.add_argument(
        "-patch-name",
        "--patch-name",
        metavar="<string>",
        required=True,
        type=str,
        help="Name of the patch that has been linted",
    )
    return parser.parse_args()

def generate_markdown(linter_log: str, patch_name: str, outdir: str="./linter_fail_report.md"):
    header = f"""---
title: check_GNU_style.py {patch_name}
labels: linter-failure
---
The following issues have been found with {patch_name}.
Please use your best judgement when resolving these issues. These are only warnings and do not need to be resolved in order to merge your patch.
If any of these warnings seem like false-positives that could be guarded against please contact me: patrick@rivosinc.com.

"""

    with open(f"./{linter_log}", "r", encoding="UTF-8") as log:
        with open(f"./{outdir}", "w", encoding="UTF-8") as file:
            file.write(str(header))
            file.write(str("```\n"))
            file.write(str(log.read()))
            file.write(str("```\n"))

def main():
    args = parse_arguments()
    generate_markdown(args.linter_log, args.patch_name)

if __name__ == "__main__":
    main()
