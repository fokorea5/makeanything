"""DB 스키마 정의."""


def init_schema(conn):
    """테이블 생성."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER DEFAULT 0
        )
    """)
    conn.commit()
