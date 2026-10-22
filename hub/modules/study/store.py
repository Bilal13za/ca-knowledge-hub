"""Study store: decks, cards, SM-2 reviews, questions, planner (Phase 14)."""
from __future__ import annotations

from datetime import date, timedelta

from . import sm2

ACTIVITY_MINUTES = {
    "read": 30,
    "flashcards": 20,
    "questions": 45,
    "review": 30,
}


# ---------------------------------------------------------------- decks/cards

def list_decks(conn) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT d.*, COUNT(c.id) AS cards,
                  SUM(CASE WHEN r.next_due IS NULL OR r.next_due <= date('now')
                           THEN 1 ELSE 0 END) AS due
           FROM study_decks d
           LEFT JOIN study_cards c ON c.deck_id = d.id
           LEFT JOIN study_reviews r ON r.card_id = c.id
           GROUP BY d.id ORDER BY d.id""")]


def add_card(conn, *, deck_id: str, front: str, back: str,
             chapter_ref: str = "", page_ref: str = "",
             source_ref: str = "") -> int:
    if not front.strip() or not back.strip():
        raise ValueError("Card front and back are required.")
    cur = conn.execute(
        """INSERT INTO study_cards (deck_id, front, back, chapter_ref,
           page_ref, source_ref) VALUES (?,?,?,?,?,?)""",
        (deck_id, front, back, chapter_ref, page_ref, source_ref))
    conn.commit()
    return cur.lastrowid


def get_card(conn, card_id: int) -> dict:
    r = conn.execute("SELECT * FROM study_cards WHERE id = ?",
                     (card_id,)).fetchone()
    if r is None:
        raise ValueError(f"Unknown card {card_id}")
    d = dict(r)
    d["review"] = get_review(conn, card_id)
    return d


def get_review(conn, card_id: int) -> dict | None:
    r = conn.execute("SELECT * FROM study_reviews WHERE card_id = ?",
                     (card_id,)).fetchone()
    return dict(r) if r else None


def review_card(conn, card_id: int, rating: str,
                today: date | None = None) -> dict:
    """Apply an SM-2 review; persists the new state. Returns the state."""
    get_card(conn, card_id)  # validates existence
    state = sm2.next_state(get_review(conn, card_id), rating, today)
    conn.execute(
        """INSERT INTO study_reviews
           (card_id, ease, interval_days, reps, lapses, next_due,
            last_reviewed, last_rating)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(card_id) DO UPDATE SET
             ease=excluded.ease, interval_days=excluded.interval_days,
             reps=excluded.reps, lapses=excluded.lapses,
             next_due=excluded.next_due,
             last_reviewed=excluded.last_reviewed,
             last_rating=excluded.last_rating""",
        (card_id, state["ease"], state["interval_days"], state["reps"],
         state["lapses"], state["next_due"], state["last_reviewed"],
         state["last_rating"]))
    conn.commit()
    return state


def due_cards(conn, deck_id: str | None = None,
              today: date | None = None, limit: int | None = None) -> list[dict]:
    """Cards due for review (never-reviewed first, then by due date)."""
    today_s = (today or date.today()).isoformat()
    sql = """SELECT c.*, r.ease, r.interval_days, r.reps, r.lapses,
                    r.next_due, r.last_reviewed, r.last_rating
             FROM study_cards c LEFT JOIN study_reviews r
               ON r.card_id = c.id
             WHERE (r.next_due IS NULL OR r.next_due <= ?)"""
    params: list = [today_s]
    if deck_id:
        sql += " AND c.deck_id = ?"
        params.append(deck_id)
    sql += (" ORDER BY CASE WHEN r.next_due IS NULL THEN 0 ELSE 1 END,"
            " r.next_due, c.id")
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return [dict(r) for r in conn.execute(sql, params)]


# ---------------------------------------------------------------- questions

def list_questions(conn, deck_id: str | None = None) -> list[dict]:
    sql = "SELECT * FROM study_questions"
    params: list = []
    if deck_id:
        sql += " WHERE deck_id = ?"
        params.append(deck_id)
    sql += " ORDER BY deck_id, number"
    return [dict(r) for r in conn.execute(sql, params)]


def get_question(conn, question_id: str) -> dict:
    r = conn.execute("SELECT * FROM study_questions WHERE id = ?",
                     (question_id,)).fetchone()
    if r is None:
        raise ValueError(f"Unknown question {question_id}")
    return dict(r)


def record_attempt(conn, *, question_id: str, correct: int,
                   notes: str = "") -> int:
    get_question(conn, question_id)  # validates
    if correct not in (0, 1):
        raise ValueError("correct must be 0 or 1 (self-marked).")
    cur = conn.execute(
        "INSERT INTO study_attempts (question_id, correct, notes)"
        " VALUES (?,?,?)", (question_id, correct, notes))
    conn.commit()
    return cur.lastrowid


def question_stats(conn) -> dict:
    """Per-question correct rate (weak-first ordering for the planner)."""
    rows = conn.execute(
        """SELECT question_id, COUNT(*) AS n,
                  SUM(correct) AS ok
           FROM study_attempts GROUP BY question_id""").fetchall()
    return {r["question_id"]: {"attempts": r["n"],
                               "rate": (r["ok"] or 0) / r["n"]}
            for r in rows}


# ---------------------------------------------------------------- planner

def generate_plan(conn, *, name: str, exam_date: str,
                  hours_per_day: float = 1.0,
                  study_days: list[int] | None = None,
                  today: date | None = None) -> int:
    """Build a deterministic day-by-day plan from tomorrow to exam_date.

    Activities cycle per study day: read a chapter, review due
    flashcards, solve chapter questions — weak chapters first (by
    card lapse rate, then question accuracy, then chapter order).
    Respects hours_per_day via the activity-minute catalogue.
    """
    today = today or date.today()
    exam = date.fromisoformat(exam_date)
    if exam <= today:
        raise ValueError("exam_date must be in the future.")
    study_days = study_days if study_days is not None else [0, 1, 2, 3, 4, 5, 6]
    if not name.strip():
        raise ValueError("Plan name is required.")

    decks = [d for d in list_decks(conn) if d["cards"] > 0]
    weak_first = sorted(
        decks,
        key=lambda d: (
            -(d["due"] or 0) / max(d["cards"], 1),  # most due first
            d["id"],
        ))

    cur = conn.execute(
        "INSERT INTO study_plans (name, exam_date, hours_per_day, study_days)"
        " VALUES (?,?,?,?)",
        (name, exam_date, hours_per_day,
         __import__("json").dumps(study_days)))
    plan_id = cur.lastrowid

    budget = int(hours_per_day * 60)
    day = today + timedelta(days=1)
    di = 0
    while day <= exam:
        if day.weekday() in study_days and weak_first:
            deck = weak_first[di % len(weak_first)]
            items = [
                ("read", f"Read {deck['name']}", "read"),
                ("flashcards",
                 f"Review due flashcards — {deck['name']}", "flashcards"),
                ("questions",
                 f"Solve practice questions — {deck['name']}", "questions"),
            ]
            spent = 0
            for atype, title, _ in items:
                mins = ACTIVITY_MINUTES[atype]
                if spent + mins > budget:
                    break
                conn.execute(
                    """INSERT INTO study_plan_items
                       (plan_id, activity_date, activity_type, title, minutes)
                       VALUES (?,?,?,?,?)""",
                    (plan_id, day.isoformat(), atype, title, mins))
                spent += mins
            di += 1
        day += timedelta(days=1)
    conn.commit()
    return plan_id


def list_plans(conn) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT p.*, COUNT(i.id) AS items,
                  SUM(i.done) AS done_items
           FROM study_plans p LEFT JOIN study_plan_items i
             ON i.plan_id = p.id
           GROUP BY p.id ORDER BY p.id DESC""")]


def plan_items(conn, plan_id: int, activity_date: str | None = None) -> list[dict]:
    sql = "SELECT * FROM study_plan_items WHERE plan_id = ?"
    params: list = [plan_id]
    if activity_date:
        sql += " AND activity_date = ?"
        params.append(activity_date)
    sql += " ORDER BY activity_date, id"
    return [dict(r) for r in conn.execute(sql, params)]


def mark_item_done(conn, item_id: int, done: bool = True) -> None:
    conn.execute("UPDATE study_plan_items SET done = ? WHERE id = ?",
                 (1 if done else 0, item_id))
    conn.commit()
