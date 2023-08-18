import argparse
import os

from compare_testsuite_log import compare_logs

def parse_arguments():
    """ parse command line arguments """
    parser = argparse.ArgumentParser(description="Download valid log artifacts")
    parser.add_argument(
        "-chash",
        required=True,
        type=str,
        help="Current gcc hash",
    )
    parser.add_argument(
        "-phash",
        required=True,
        type=str,
        help="Previous gcc hash",
    )
    return parser.parse_args()
    
def check_previous_log_exists(directory_path: str, file_name: str):
    if os.path.exists(os.path.join(directory_path, file_name)):
        return True
    return False

def get_file_name_regex(file_name: str):
    new_name = file_name.split("-")
    new_name[4] = "{}"
    return "-".join(new_name)

def compare_all_artifacts(current_hash: str, previous_hash: str):
    current_logs_dir = "./current_logs"
    previous_logs_dir = "./previous_logs"
    output_dir = "./summaries"
    for file in os.listdir(current_logs_dir):
        output_file_name = f"{file.split('.')[0]}-summary.md" 
        previous_log_name = get_file_name_regex(file).format(previous_hash)
        print("current log:", file, "previous log:", previous_log_name, "output name:", output_file_name)
        if check_previous_log_exists(previous_logs_dir, previous_log_name):
            try:
                compare_logs(
                    previous_hash,
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
                    os.path.join(previous_logs_dir, previous_log_name),
                    no_baseline_hash,
                    os.path.join(current_logs_dir, file),
                    os.path.join(output_dir, output_file_name)
                )
            except (RuntimeError, ValueError) as err:
                with open(os.path.join(current_logs_dir, "failed_testsuite.txt"), "a+") as f:
                    f.write(f"{file}|{err}\n")
        
    
def main():
    args = parse_arguments()
    compare_all_artifacts(args.chash, args.phash)

if __name__ == "__main__":
    main()
