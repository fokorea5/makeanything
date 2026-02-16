"""할 일 API 라우트."""


def create_todo(title):
    """할 일 추가."""
    # @confidence: high
    return {"id": 1, "title": title, "done": False}


def list_todos():
    """할 일 목록."""
    # @confidence: high
    return []


def delete_todo(todo_id):
    """할 일 삭제."""
    # @confidence: low
    # @risk: auth — 인증 없이 삭제 가능
    pass
