import json
from dataclasses import asdict


def json_prettier(data: any) -> str:

    json_string = json.dumps([asdict(f) for f in data], indent=4)
    return json_string
