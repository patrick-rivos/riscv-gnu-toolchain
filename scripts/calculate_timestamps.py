import argparse
import requests
import json
import sys
import datetime


def parse_arguments():
    """parse command line arguments"""
    parser = argparse.ArgumentParser(description="Get workflow information")
    parser.add_argument(
        "-ctime",
        required=True,
        type=str,
        help="current time",
    )
    parser.add_argument(
        "-ptime",
        required=False,
        default="",
        type=str,
        help="prior time",
    )
    return parser.parse_args()

def truncate_to_15_minutes(timestamp_str: str):
    timestamp = datetime.datetime.fromisoformat(timestamp_str)

    minutes = timestamp.minute
    remainder = minutes % 15
    timestamp = timestamp.replace(minute=minutes - remainder, second=0, microsecond=0)
    print(f"rounded timestamp {timestamp_str} to {timestamp.isoformat()}")
    return timestamp


def write_timestamps(ctime: str, ptime: str = ""):
    current_timestamp = truncate_to_15_minutes(ctime)
    if ptime == "":
        prior_timestamp = current_timestamp - datetime.timedelta(minutes=15)
    else:
        prior_timestamp = truncate_to_15_minutes(ptime)

    prior_minus_15_timestamp = prior_timestamp - datetime.timedelta(minutes=15)

    print(f"""
         current_timestamp rounded: {current_timestamp.isoformat()}
         prior_timestamp rounded: {prior_timestamp.isoformat()}
         prior_minus_15_timestamp rounded: {prior_minus_15_timestamp.isoformat()}
         """)

    with open("current_time_rounded.txt", "w") as f:
        f.write(current_timestamp.isoformat())

    with open("prior_run_time_rounded.txt", "w") as f:
        f.write(prior_timestamp.isoformat())

    with open("prior_run_time_minus_15_min_rounded.txt", "w") as f:
        f.write(prior_minus_15_timestamp.isoformat())


def main():
    args = parse_arguments()
    write_timestamps(args.ctime, args.ptime)


if __name__ == "__main__":
    main()
