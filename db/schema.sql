-- 교훈 데이터베이스 스키마
-- lessons_db.py가 자동으로 테이블을 생성하지만
-- 수동 참조용으로 스키마를 기록합니다.

CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    detail TEXT NOT NULL,
    tags TEXT DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lessons_project ON lessons(project);
CREATE INDEX IF NOT EXISTS idx_lessons_category ON lessons(category);
