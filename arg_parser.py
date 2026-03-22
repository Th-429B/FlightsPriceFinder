import argparse
from fast_flights import Airport
from datetime import datetime

def valid_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(
            "Date must be in YYYY-MM-DD format"
        )

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--start", type=Airport, required=True)
    parser.add_argument("--end", type=Airport, required=True)
    parser.add_argument("--date", type=valid_date, required=True)
    parser.add_argument("--debug", type=bool)

    args = parser.parse_args()

    if args.debug:
        print("Debug mode enabled")
        print(args.start.value)
        print(args.end.value)
        print(args.date.strftime("%Y-%m-%d"))

    return args.start.value, args.end.value, args.date.strftime("%Y-%m-%d"), args.debug
