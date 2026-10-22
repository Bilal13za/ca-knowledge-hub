"""Phase 1C acceptance: knowledge CRUD, versioning, review-due, relations."""
import pytest

from hubcore import knowledge


def test_create_and_get(conn):
    rid = knowledge.create_record(conn, {
        "module": "audit", "topic": "risk", "title": "R1",
        "content": "body", "verification_status": "verified",
        "extension_json": {"assertions": ["occurrence"]},
    })
    rec = knowledge.get_record(conn, rid)
    assert rec["title"] == "R1" and rec["verification_status"] == "verified"


def test_create_rejects_bad_status_and_bad_json(conn):
    with pytest.raises(ValueError):
        knowledge.create_record(conn, {"title": "x", "verification_status": "bogus"})
    with pytest.raises(ValueError):
        knowledge.create_record(conn, {"title": "x", "extension_json": "{nope"})


def test_revise_versions_and_preserves_history(conn):
    rid = knowledge.create_record(conn, {
        "title": "Rule", "content": "v1", "verification_status": "verified",
    })
    v = knowledge.revise_record(
        conn, rid, {"content": "v2", "verification_status": "verified"},
        reason="rate updated", source_of_change="FBR notification",
    )
    assert v == 1
    rec = knowledge.get_record(conn, rid)
    assert rec["content"] == "v2"
    hist = conn.execute(
        "SELECT * FROM revision_history WHERE entity_id=?", (rid,)
    ).fetchone()
    assert hist["reason"] == "rate updated"
    assert "v1" in hist["previous_content_json"]


def test_delete_keeps_revision_history(conn):
    rid = knowledge.create_record(conn, {"title": "Temp", "content": "x"})
    knowledge.revise_record(conn, rid, {"content": "y"}, reason="fix")
    knowledge.delete_record(conn, rid)
    assert knowledge.get_record(conn, rid) is None
    assert conn.execute(
        "SELECT COUNT(*) FROM revision_history WHERE entity_id=?", (rid,)
    ).fetchone()[0] == 1  # history survives deletion


def test_due_for_review(conn):
    knowledge.create_record(conn, {
        "title": "Old rule", "verification_status": "verified",
        "review_due_date": "2020-01-01",
    })
    knowledge.create_record(conn, {
        "title": "Fresh rule", "verification_status": "verified",
        "review_due_date": "2999-01-01",
    })
    knowledge.create_record(conn, {
        "title": "Superseded old", "verification_status": "superseded",
        "review_due_date": "2020-01-01",
    })
    due = knowledge.due_for_review(conn)
    titles = {r["title"] for r in due}
    assert titles == {"Old rule"}  # fresh excluded, superseded excluded


def test_cross_module_relations(conn):
    a = knowledge.create_record(conn, {"module": "audit", "title": "Provision audit"})
    t = knowledge.create_record(conn, {"module": "tax", "title": "Provision tax rule"})
    knowledge.add_relation(conn, a, t, rel_type="has-tax-implication",
                           note="provisions affect taxable income")
    rels = knowledge.get_relations(conn, a)
    assert len(rels) == 1 and rels[0]["other_module"] == "tax"
    # incoming direction from the tax side
    rels_t = knowledge.get_relations(conn, t)
    assert rels_t[0]["direction"] == "incoming"
    # prompt helper: tax link visible from an audit-only workspace
    others = knowledge.related_in_other_modules(conn, a, ["audit"])
    assert len(others) == 1
    assert knowledge.related_in_other_modules(conn, a, ["audit", "tax"]) == []
    with pytest.raises(ValueError):
        knowledge.add_relation(conn, a, a)


def test_extension_schema_validation():
    schema = {"type": "object",
              "properties": {"assertions": {"type": "array"},
                             "year": {"type": "integer"}}}
    assert knowledge.validate_extension_against_schema(
        {"assertions": ["a"], "year": 2026}, schema) == []
    problems = knowledge.validate_extension_against_schema(
        {"assertions": "nope", "year": "2026"}, schema)
    assert len(problems) == 2


def test_list_records_filters(conn):
    knowledge.create_record(conn, {"module": "audit", "topic": "r", "title": "A1",
                                   "verification_status": "verified"})
    knowledge.create_record(conn, {"module": "audit", "topic": "r", "title": "A2",
                                   "verification_status": "user_note"})
    assert len(knowledge.list_records(conn, module="audit")) == 2
    assert len(knowledge.list_records(conn, module="audit",
                                      verification_status="verified")) == 1
