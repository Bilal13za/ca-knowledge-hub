"""Phase 1C acceptance: workspace CRUD and validation."""
from hubcore import workspaces


def test_crud(conn):
    wid = workspaces.create_workspace(conn, "Audit + Tax", ["tax", "audit", "audit"])
    ws = workspaces.get_workspace(conn, wid)
    assert ws["name"] == "Audit + Tax"
    assert ws["modules"] == ["audit", "tax"]  # deduped + sorted
    assert workspaces.get_workspace_by_name(conn, "Audit + Tax")["id"] == wid
    workspaces.update_workspace(conn, wid, modules=["audit"])
    assert workspaces.workspace_modules(conn, wid) == ["audit"]
    workspaces.delete_workspace(conn, wid)
    assert workspaces.get_workspace(conn, wid) is None


def test_list_ordered_by_last_used(conn):
    a = workspaces.create_workspace(conn, "A", ["audit"])
    b = workspaces.create_workspace(conn, "B", ["tax"])
    workspaces.touch_workspace(conn, a)
    names = [w["name"] for w in workspaces.list_workspaces(conn)]
    assert names[0] == "A"


def test_validate_flags_missing_modules(conn):
    wid = workspaces.create_workspace(conn, "W", ["audit", "ghost"])
    result = workspaces.validate_workspace(conn, wid, ["audit", "tax"])
    assert result["missing"] == ["ghost"] and not result["ok"]
    ok = workspaces.validate_workspace(conn, wid, ["audit", "tax", "ghost"])
    assert ok["ok"]
