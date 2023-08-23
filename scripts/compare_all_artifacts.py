import argparse
import re
import os

from compare_testsuite_log import compare_logs

def parse_arguments():
    """ parse command line arguments """
    parser = argparse.ArgumentParser(description="Download valid log artifacts")
    parser.add_argument(
        "-hash",
        required=True,
        type=str,
        help="Current gcc hash",
    )
    return parser.parse_args()
    
def find_previous_log(directory_path: str, file_regex: str):
    dir_contents = " ".join(os.listdir(directory_path))
    logs = re.findall(file_regex, dir_contents)
    if logs != []:
        return logs[0]
    return ""

def get_file_name_regex(file_name: str):
    new_name = file_name.split("-")
    new_name[4] = "[^-]*"
    return "-".join(new_name)

def get_hash_from_file_name(file_name: str):
    return file_name.split("-")[4]

def compare_all_artifacts(current_hash: str):
    current_logs_dir = "./current_logs"
    previous_logs_dir = "./previous_logs"
    output_dir = "./summaries"
    for file in os.listdir(current_logs_dir):
        if "-" not in file: # failed_testsuite and failed_build check
            continue
        output_file_name = f"{file.split('.')[0]}-summary.md" 
        previous_log_regex = get_file_name_regex(file)
        previous_log_name = find_previous_log(previous_logs_dir, previous_log_regex)
        print("current log:", file, "previous log:", previous_log_name, "output name:", output_file_name)
        if previous_log_name != "":
            try:
                print(f"found previous log. comparing {os.path.join(previous_logs_dir, previous_log_name)} with {os.path.join(current_logs_dir, file)}")
                compare_logs(
                    get_hash_from_file_name(previous_log_name),
                    os.path.join(previous_logs_dir, previous_log_name),
                    current_hash,
                    os.path.join(current_logs_dir, file),
                    os.path.join(output_dir, output_file_name)
                )
            except (RuntimeError, ValueError) as err:
                with open(os.path.join(current_logs_dir, "failed_testsuite.txt"), "a+") as f:
                    f.write(f"{file}|{err}\n")
        else:
            try:
                no_baseline_hash = current_hash + "-no-baseline"
                compare_logs(
                    no_baseline_hash,
                    os.path.join(current_logs_dir, file),
                    no_baseline_hash,
                    os.path.join(current_logs_dir, file),
                    os.path.join(output_dir, output_file_name)
                )
            except (RuntimeError, ValueError) as err:
                with open(os.path.join(current_logs_dir, "failed_testsuite.txt"), "a+") as f:
                    f.write(f"{file}|{err}\n")
        
    
def main():
    args = parse_arguments()
    compare_all_artifacts(args.hash)

if __name__ == "__main__":
    main()
