"""Phase 14 acceptance: SM-2 engine, pack seed, planner."""
import json
import sys
from datetime import date
from pathlib import Path

import pytest

HUB = Path(__file__).resolve().parent.parent
if str(HUB) not in sys.path:
    sys.path.insert(0, str(HUB))

from hubcore import registry
from hubcore import search as searchmod
from modules.study import seed as seedmod
from modules.study import sm2, store


@pytest.fixture()
def seeded(conn):
    counts = seedmod.seed_study(conn)
    conn.commit()
    return counts


def test_sm2_first_good_review():
    # First 'good': reps=1, interval=1, EF adjusted: 2.5+(0.1-1*(0.08+0.02))=2.5
    s = sm2.next_state(None, "good", date(2026, 10, 21))
    assert s["reps"] == 1 and s["interval_days"] == 1
    assert s["next_due"] == "2026-10-22"
    assert s["ease"] == 2.5


def test_sm2_progression_and_lapse():
    t = date(2026, 10, 21)
    s1 = sm2.next_state(None, "good", t)          # reps 1, int 1
    s2 = sm2.next_state(s1, "good", t)            # reps 2, int 6
    assert s2["interval_days"] == 6
    s3 = sm2.next_state(s2, "good", t)           # reps 3, int round(6*2.5)=15
    assert s3["interval_days"] == 15
    s4 = sm2.next_state(s3, "again", t)          # lapse: reset
    assert s4["reps"] == 0 and s4["interval_days"] == 1
    assert s4["lapses"] == 1
    assert s4["ease"] < s3["ease"]               # EF dropped
    with pytest.raises(ValueError):
        sm2.next_state(None, "meh", t)


def test_sm2_hard_is_conservative():
    t = date(2026, 10, 21)
    s1 = sm2.next_state(None, "good", t)
    s2 = sm2.next_state(s1, "good", t)            # interval 6
    s3 = sm2.next_state(s2, "hard", t)            # max(1, round(6*1.2)) = 7
    assert s3["interval_days"] == 7               # not round(6*ease)=15


def test_sm2_is_due():
    assert sm2.is_due(None) is True
    assert sm2.is_due({"next_due": "2020-01-01"},
                      date(2026, 10, 21)) is True
    assert sm2.is_due({"next_due": "2099-01-01"},
                      date(2026, 10, 21)) is False


def test_seed_pack_counts(seeded):
    assert seeded["study_decks"] == 15  # 14 chapters + definitions
    assert seeded["study_cards"] == 14
    assert seeded["study_questions"] == 131
    assert seeded["knowledge_records(study)"] == 17  # 2 guides + 15 decks


def test_seed_idempotent(seeded, conn):
    assert seedmod.seed_study(conn)["study_questions"] == 131


def test_review_lifecycle(seeded, conn):
    card = store.due_cards(conn)[0]
    state = store.review_card(conn, card["id"], "good",
                              date(2026, 10, 21))
    assert state["next_due"] == "2026-10-22"
    assert store.get_review(conn, card["id"])["reps"] == 1
    # due list shrinks for that card (due tomorrow, not today)
    assert card["id"] not in {c["id"] for c in
                              store.due_cards(conn,
                                              today=date(2026, 10, 21))}
    cid = store.add_card(conn, deck_id="capttax-definitions",
                         front="Q", back="A")
    assert store.get_card(conn, cid)["front"] == "Q"
    with pytest.raises(ValueError):
        store.add_card(conn, deck_id="capttax-definitions",
                       front=" ", back="A")
    with pytest.raises(ValueError):
        store.review_card(conn, 99999, "good")


def test_question_attempts(seeded, conn):
    q = store.list_questions(conn)[0]
    store.record_attempt(conn, question_id=q["id"], correct=1)
    store.record_attempt(conn, question_id=q["id"], correct=0)
    stats = store.question_stats(conn)
    assert stats[q["id"]] == {"attempts": 2, "rate": 0.5}
    with pytest.raises(ValueError):
        store.record_attempt(conn, question_id=q["id"], correct=2)
    with pytest.raises(ValueError):
        store.record_attempt(conn, question_id="nope", correct=1)


def test_planner_deterministic(seeded, conn):
    pid = store.generate_plan(conn, name="T", exam_date="2026-11-04",
                              hours_per_day=2.0,
                              today=date(2026, 10, 21))
    items = store.plan_items(conn, pid)
    assert items, "plan should have items"
    assert all(i["activity_date"] > "2026-10-21" for i in items)
    assert all(i["activity_date"] <= "2026-11-04" for i in items)
    assert sum(i["minutes"] for i in items
               if i["activity_date"] == items[0]["activity_date"]) <= 120
    # deterministic: same inputs -> same titles in same order
    pid2 = store.generate_plan(conn, name="T2", exam_date="2026-11-04",
                               hours_per_day=2.0,
                               today=date(2026, 10, 21))
    t1 = [(i["activity_date"], i["title"]) for i in
          store.plan_items(conn, pid)]
    t2 = [(i["activity_date"], i["title"]) for i in
          store.plan_items(conn, pid2)]
    assert t1 == t2
    store.mark_item_done(conn, items[0]["id"])
    assert store.plan_items(conn, pid)[0]["done"] == 1
    with pytest.raises(ValueError):
        store.generate_plan(conn, name="x", exam_date="2020-01-01")


def test_global_search_finds_decks(seeded, conn):
    res = searchmod.search_records(conn, "flashcards", modules=["study"])
    assert res and res[0]["module"] == "study"


def test_manifest_and_pages():
    data = json.loads(
        (HUB / "modules" / "study" / "module.json").read_text(
            encoding="utf-8"))
    registry.validate_manifest(data)
    mod = registry.ModuleInfo(name=data["name"], title=data["title"],
                              version=data["version"],
                              description=data["description"],
                              manifest=data)
    pages = registry.load_ui_pages(mod)
    assert {p["id"] for p in pages} == {
        "st_flashcards", "st_questions", "st_planner"}
    for p in pages:
        assert callable(p["render"])
