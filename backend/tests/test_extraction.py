from app.clause_types import ClauseType, ALL_CLAUSE_TYPES


def test_seven_named_clause_types():
    assert len(ALL_CLAUSE_TYPES) == 7
    assert ClauseType.INDEMNITY in ALL_CLAUSE_TYPES
    assert ClauseType.LIMITATION_OF_LIABILITY.value == "limitation_of_liability"
