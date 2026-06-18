from app.baseline.loader import load_baseline, save_baseline
from app.clause_types import ALL_CLAUSE_TYPES


def test_baseline_has_entry_for_every_clause_type():
    b = load_baseline()
    for t in ALL_CLAUSE_TYPES:
        assert t.value in b and b[t.value]


def test_save_and_reload_baseline(tmp_path):
    path = tmp_path / "b.json"
    save_baseline({"indemnity": "custom"}, path=str(path))
    assert load_baseline(path=str(path))["indemnity"] == "custom"
