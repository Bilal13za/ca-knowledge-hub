"""Phase 14 seeder: Study Mode (CAPT content pack — Bilal's private data)."""
from __future__ import annotations

import json
from pathlib import Path

PACK_NOTE = ("Bilal's personal study data (Murtaza Quaid, Taxation: "
             "Principles and Compliance). Private to his install — "
             "never redistributed.")


def seed_study(conn, data_dir=None) -> dict:
    data_dir = Path(data_dir) if data_dir else Path(__file__).parent / "data"
    conn.executescript(
        (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))
    pack = json.loads(
        (data_dir / "content_pack.json").read_text(encoding="utf-8"))

    # Decks: one per chapter.
    for ch in pack["chapters"]:
        deck_id = f"capttax-{ch['id']}"
        conn.execute(
            """INSERT INTO study_decks (id, name, source, description)
               VALUES (?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, source=excluded.source,
                 description=excluded.description""",
            (deck_id, f"Ch {ch['number']}: {ch['title']}",
             PACK_NOTE,
             f"Pages {ch['page_start']}–{ch['page_end']}"))
    conn.execute(
        """INSERT INTO study_decks (id, name, source, description)
           VALUES ('capttax-definitions','Key definitions',?,?)
           ON CONFLICT(id) DO NOTHING""",
        (PACK_NOTE, "14 auto-detected definitions from the book."))

    # Definitions -> flashcards.
    for d in pack["definitions"]:
        exists = conn.execute(
            "SELECT 1 FROM study_cards WHERE front = ? AND deck_id = ?",
            (d["term"], "capttax-definitions")).fetchone()
        if not exists:
            conn.execute(
                """INSERT INTO study_cards
                   (deck_id, front, back, chapter_ref, page_ref, source_ref)
                   VALUES (?,?,?,?,?,?)""",
                ("capttax-definitions", d["term"], d["definition"],
                 d.get("chapter_id"), str(d.get("page") or ""),
                 f"Book {d.get('section_ref') or ''}".strip()))
    conn.commit()

    # Questions -> question bank.
    for q in pack["questions"]:
        conn.execute(
            """INSERT INTO study_questions
               (id, deck_id, number, statement, solution, has_solution,
                page_ref, source_ref)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 statement=excluded.statement, solution=excluded.solution,
                 has_solution=excluded.has_solution""",
            (q["id"], f"capttax-{q['chapter_id']}", str(q.get("number")),
             q["statement"], q.get("solution"),
             1 if q.get("has_solution") else 0,
             f"{q.get('page_start') or ''}–{q.get('page_end') or ''}",
             q.get("origin") or ""))
    conn.commit()

    decks = conn.execute("SELECT COUNT(*) FROM study_decks").fetchone()[0]
    cards = conn.execute("SELECT COUNT(*) FROM study_cards").fetchone()[0]
    questions = conn.execute(
        "SELECT COUNT(*) FROM study_questions").fetchone()[0]
    stubs = _register_stubs(conn)
    conn.commit()
    return {"study_decks": decks, "study_cards": cards,
            "study_questions": questions,
            "knowledge_records(study)": stubs}


def _register_stubs(conn) -> int:
    conn.execute("DELETE FROM record_fts WHERE module='study'")
    conn.execute("DELETE FROM knowledge_records WHERE module='study'")
    guides = [
        ("Study Mode",
         "SM-2 flashcards, a 131-question practice bank from your tax "
         "textbook, and a deterministic revision planner. Your study "
         "data — private to this install.",
         "study,flashcards,revision,sm2"),
        ("Revision planner",
         "Generates a day-by-day plan from tomorrow to your exam date, "
         "weak chapters first, respecting your daily hours. Deterministic "
         "— the same inputs always give the same plan.",
         "study,planner,revision plan"),
    ]
    n = 0
    for title, desc, kw in guides:
        cur = conn.execute(
            """INSERT INTO knowledge_records
               (module, topic, title, description, keywords, content,
                verification_status, extension_json)
               VALUES ('study','guide',?,?,?,?, 'user_note', '{}')""",
            (title, desc, kw, f"{title}. {desc}"))
        rid = cur.lastrowid
        conn.execute(
            "INSERT INTO record_fts (title, description, keywords, content,"
            " record_id, module) VALUES (?,?,?,?,?,?)",
            (title, desc, kw, f"{title}. {desc}", rid, "study"))
        n += 1
    # chapter decks searchable too
    for r in conn.execute("SELECT * FROM study_decks ORDER BY id"):
        title = f"Study deck: {r['name']}"
        cur = conn.execute(
            """INSERT INTO knowledge_records
               (module, topic, title, description, keywords, content,
                verification_status, extension_json)
               VALUES ('study','deck',?,?,?,?, 'user_note', ?)""",
            (title, r["description"] or "", "study deck chapter",
             f"{title}. {r['description'] or ''}",
             json.dumps({"study_deck": r["id"]})))
        rid = cur.lastrowid
        conn.execute(
            "INSERT INTO record_fts (title, description, keywords, content,"
            " record_id, module) VALUES (?,?,?,?,?,?)",
            (title, r["description"] or "", "study deck chapter",
             f"{title}. {r['description'] or ''}", rid, "study"))
        n += 1
    conn.commit()
    return n
