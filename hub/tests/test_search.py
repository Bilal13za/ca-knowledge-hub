"""Phase 1C acceptance: global search with workspace scoping."""
from hubcore import knowledge, search


def _seed(conn):
    knowledge.create_record(conn, {
        "module": "audit", "topic": "risk", "title": "Revenue recognition risk",
        "content": "Premature revenue recognition overstates profit.",
        "verification_status": "verified",
    })
    knowledge.create_record(conn, {
        "module": "tax", "topic": "wht", "title": "Withholding on services",
        "content": "WHT applies to payments for services rendered.",
        "verification_status": "extracted_unverified",
    })


def test_global_search_finds_both_domains(conn):
    _seed(conn)
    res = search.global_search(conn, "revenue")
    assert any("audit" == r["module"] for r in res["records"])


def test_workspace_scoping_filters_modules(conn):
    _seed(conn)
    scoped = search.search_records(conn, "services", modules=["audit"])
    assert scoped == []  # the WHT record is tax-only
    unscoped = search.search_records(conn, "services")
    assert len(unscoped) == 1 and unscoped[0]["module"] == "tax"


def test_unsafe_query_sanitized(conn):
    _seed(conn)
    # FTS5 metacharacters must not raise
    res = search.global_search(conn, 'revenue " OR * (test):')
    assert isinstance(res["records"], list)


def test_empty_query_returns_nothing(conn):
    _seed(conn)
    assert search.search_records(conn, "   ") == []


def test_search_categories(conn):
    _seed(conn)
    assert search.search_categories(conn) == ["audit", "tax"]


def test_hits_carry_verification_status(conn):
    _seed(conn)
    res = search.search_records(conn, "withholding")
    assert res[0]["verification_status"] == "extracted_unverified"
    assert "<b>" in res[0]["snippet"]
