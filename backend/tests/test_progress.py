from app.pipeline.progress import set_progress, get_progress, clear_progress


def test_set_get_clear_roundtrip():
    clear_progress(999)
    assert get_progress(999) is None
    set_progress(999, stage="structuring", current=1, total=3, preview="hello")
    p = get_progress(999)
    assert p == {"stage": "structuring", "current": 1, "total": 3, "preview": "hello"}
    set_progress(999, current=2)  # partial update merges
    assert get_progress(999)["current"] == 2
    assert get_progress(999)["total"] == 3
    clear_progress(999)
    assert get_progress(999) is None
