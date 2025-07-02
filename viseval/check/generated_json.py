from json_repair import repair_json


def clean_json(json_string):
    # Strip a possible preamble before the actual JSON data-structure.
    i = json_string.find("{")
    json_string = json_string[i:]

    # Handle missing comma after a dictionary value
    json_string = json_string.replace('"\n    "', '",\n    "')

    # Fix other common issues
    return repair_json(json_string)
