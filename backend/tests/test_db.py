from sqlmodel import Session
from app.db.engine import make_engine, init_db
from app.db.models import Contract


def test_contract_persists(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path/'t.db'}")
    init_db(engine)
    with Session(engine) as s:
        c = Contract(filename="x.pdf", file_path="/tmp/x.pdf", format="pdf", status="uploaded")
        s.add(c); s.commit(); s.refresh(c)
        assert c.id is not None and c.status == "uploaded"
