import json
import os

_DEFAULT = os.path.join(os.path.dirname(__file__), "market_standard.json")


def load_baseline(path: str = _DEFAULT) -> dict[str, str]:
    with open(path) as f:
        return json.load(f)


def save_baseline(data: dict[str, str], path: str = _DEFAULT) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
