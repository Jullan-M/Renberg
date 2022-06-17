import json

def load_json(filename: str):
    with open(filename, "r", encoding="utf-8") as f:
        js = json.load(f)
    return js