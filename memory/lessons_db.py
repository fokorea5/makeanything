"""교훈 데이터베이스 — 프로젝트 postmortem 교훈을 SQLite에 저장/검색.

표준 라이브러리만 사용. 외부 의존성 없음.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "lessons.db")


def _get_conn(db_path=None):
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path=None):
    """테이블 생성. 이미 있으면 무시."""
    conn = _get_conn(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            detail TEXT NOT NULL,
            tags TEXT DEFAULT '[]',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_lesson(project, category, title, detail, tags=None, db_path=None):
    """교훈 추가. 중복(같은 project+title) 시 detail 병합."""
    conn = _get_conn(db_path)
    init_db(db_path)

    existing = conn.execute(
        "SELECT id, detail FROM lessons WHERE project = ? AND title = ?",
        (project, title),
    ).fetchone()

    if existing:
        merged = existing["detail"] + "\n---\n" + detail
        conn.execute(
            "UPDATE lessons SET detail = ? WHERE id = ?",
            (merged, existing["id"]),
        )
        lesson_id = existing["id"]
    else:
        cur = conn.execute(
            "INSERT INTO lessons (project, category, title, detail, tags, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                project,
                category,
                title,
                detail,
                json.dumps(tags or [], ensure_ascii=False),
                datetime.now().isoformat(),
            ),
        )
        lesson_id = cur.lastrowid

    conn.commit()
    conn.close()
    return lesson_id


def search_lessons(keyword=None, category=None, project=None, db_path=None):
    """교훈 검색. 조건은 AND."""
    conn = _get_conn(db_path)
    init_db(db_path)

    clauses = []
    params = []

    if keyword:
        clauses.append("(title LIKE ? OR detail LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if category:
        clauses.append("category = ?")
        params.append(category)
    if project:
        clauses.append("project = ?")
        params.append(project)

    where = " AND ".join(clauses) if clauses else "1=1"
    rows = conn.execute(
        f"SELECT * FROM lessons WHERE {where} ORDER BY created_at DESC", params
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_lessons(db_path=None):
    """전체 교훈 목록."""
    return search_lessons(db_path=db_path)


def delete_lesson(lesson_id, db_path=None):
    """교훈 삭제."""
    conn = _get_conn(db_path)
    conn.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
    conn.commit()
    conn.close()
