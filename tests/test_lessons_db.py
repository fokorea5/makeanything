"""lessons_db 단위 테스트."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.lessons_db import (
    init_db,
    add_lesson,
    search_lessons,
    get_all_lessons,
    delete_lesson,
)


class TestLessonsDB(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        init_db(self.db_path)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_add_and_get(self):
        lid = add_lesson("proj1", "bug", "널 포인터", "서버 크래시", db_path=self.db_path)
        self.assertIsNotNone(lid)

        lessons = get_all_lessons(db_path=self.db_path)
        self.assertEqual(len(lessons), 1)
        self.assertEqual(lessons[0]["project"], "proj1")
        self.assertEqual(lessons[0]["title"], "널 포인터")

    def test_duplicate_merge(self):
        add_lesson("proj1", "bug", "같은 제목", "첫 번째", db_path=self.db_path)
        add_lesson("proj1", "bug", "같은 제목", "두 번째", db_path=self.db_path)

        lessons = get_all_lessons(db_path=self.db_path)
        self.assertEqual(len(lessons), 1)
        self.assertIn("첫 번째", lessons[0]["detail"])
        self.assertIn("두 번째", lessons[0]["detail"])

    def test_search_by_keyword(self):
        add_lesson("proj1", "bug", "메모리 누수", "힙 증가", db_path=self.db_path)
        add_lesson("proj1", "perf", "느린 쿼리", "인덱스 누락", db_path=self.db_path)

        results = search_lessons(keyword="메모리", db_path=self.db_path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "메모리 누수")

    def test_search_by_category(self):
        add_lesson("proj1", "bug", "버그1", "내용1", db_path=self.db_path)
        add_lesson("proj1", "perf", "성능1", "내용2", db_path=self.db_path)

        results = search_lessons(category="perf", db_path=self.db_path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["category"], "perf")

    def test_delete(self):
        lid = add_lesson("proj1", "bug", "삭제 대상", "내용", db_path=self.db_path)
        delete_lesson(lid, db_path=self.db_path)

        lessons = get_all_lessons(db_path=self.db_path)
        self.assertEqual(len(lessons), 0)


if __name__ == "__main__":
    unittest.main()
