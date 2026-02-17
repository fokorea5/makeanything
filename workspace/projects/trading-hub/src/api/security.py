"""
Trading Hub — 암호화 유틸

API 키 암호화/복호화 (cryptography Fernet 기반).
ENCRYPTION_KEY 는 .env 에서 로드.

# @risk: encryption
"""

import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken  # @confidence: low

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Fernet 인스턴스 관리
# ──────────────────────────────────────────────

_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """Fernet 인스턴스를 가져온다. ENCRYPTION_KEY 환경변수 필요."""
    # @risk: encryption
    global _fernet
    if _fernet is not None:
        return _fernet

    key = os.environ.get("ENCRYPTION_KEY", "")
    if not key:
        # 키가 없으면 자동 생성하여 경고 출력
        logger.warning(
            "ENCRYPTION_KEY 환경변수가 설정되지 않았습니다. "
            "임시 키를 생성합니다. 운영 환경에서는 반드시 .env에 설정하세요."
        )
        key = Fernet.generate_key().decode()
        os.environ["ENCRYPTION_KEY"] = key

    try:
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:
        logger.error("ENCRYPTION_KEY 형식이 올바르지 않습니다: %s", e)
        # 유효하지 않은 키 → 새 키 생성
        key = Fernet.generate_key().decode()
        os.environ["ENCRYPTION_KEY"] = key
        _fernet = Fernet(key.encode())
        logger.warning("임시 키로 대체되었습니다.")

    return _fernet


# ──────────────────────────────────────────────
# 암호화 / 복호화 API
# ──────────────────────────────────────────────

def encrypt_value(plaintext: str) -> str:
    """
    평문 문자열을 Fernet으로 암호화하여 base64 문자열로 반환한다.

    # @risk: encryption
    """
    if not plaintext:
        return ""
    f = _get_fernet()
    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """
    Fernet 암호문을 복호화하여 평문 문자열로 반환한다.

    # @risk: encryption
    """
    if not ciphertext:
        return ""
    f = _get_fernet()
    try:
        plaintext = f.decrypt(ciphertext.encode("utf-8"))
        return plaintext.decode("utf-8")
    except InvalidToken:
        logger.error("복호화 실패: 잘못된 토큰 또는 키 불일치")
        raise ValueError("복호화 실패: 키가 일치하지 않거나 손상된 데이터입니다.")


def generate_key() -> str:
    """새 Fernet 키를 생성하여 반환한다. 초기 설정 시 사용."""
    return Fernet.generate_key().decode("utf-8")


def reset_fernet() -> None:
    """Fernet 인스턴스를 초기화한다. 키 변경 시 사용."""
    global _fernet
    _fernet = None
