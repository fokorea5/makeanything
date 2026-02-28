"""
Trading Hub — 암호화/복호화 테스트

공격자 관점:
- 빈 문자열 암호화
- 잘못된 키로 복호화
- 키 미설정 시 동작
- 긴 문자열 암호화/복호화
- 특수 문자, 유니코드
- 암호문 변조 후 복호화 실패 확인
"""

import os
import sys
import pytest

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cryptography.fernet import Fernet
from src.api.security import encrypt_value, decrypt_value, generate_key, reset_fernet


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_encryption_key():
    """각 테스트 전에 깨끗한 Fernet 키 설정."""
    reset_fernet()
    key = Fernet.generate_key().decode()
    os.environ["ENCRYPTION_KEY"] = key
    yield key
    reset_fernet()
    if "ENCRYPTION_KEY" in os.environ:
        del os.environ["ENCRYPTION_KEY"]


# ──────────────────────────────────────────────
# 정상 동작 테스트
# ──────────────────────────────────────────────

def test_encrypt_decrypt_roundtrip():
    """암호화 -> 복호화 왕복 확인."""
    plaintext = "my_secret_api_key_12345"
    encrypted = encrypt_value(plaintext)
    assert encrypted != plaintext  # 암호화됨
    assert encrypted != ""
    decrypted = decrypt_value(encrypted)
    assert decrypted == plaintext


def test_encrypt_produces_different_ciphertexts():
    """같은 평문도 매번 다른 암호문 생성 (Fernet은 타임스탬프/IV 포함)."""
    plaintext = "same_value"
    enc1 = encrypt_value(plaintext)
    enc2 = encrypt_value(plaintext)
    # Fernet은 매번 다른 암호문 생성 (nonce/timestamp)
    assert enc1 != enc2
    # 하지만 둘 다 같은 평문으로 복호화
    assert decrypt_value(enc1) == plaintext
    assert decrypt_value(enc2) == plaintext


def test_generate_key_format():
    """생성된 키가 유효한 Fernet 키 형식인지 확인."""
    key = generate_key()
    assert isinstance(key, str)
    assert len(key) == 44  # Fernet 키는 base64로 44자
    # 유효한 Fernet 키인지 확인
    Fernet(key.encode())  # 에러 없어야 함


# ──────────────────────────────────────────────
# 경계값 테스트
# ──────────────────────────────────────────────

def test_encrypt_empty_string():
    """빈 문자열 암호화 시 빈 문자열 반환."""
    result = encrypt_value("")
    assert result == ""


def test_decrypt_empty_string():
    """빈 문자열 복호화 시 빈 문자열 반환."""
    result = decrypt_value("")
    assert result == ""


def test_encrypt_unicode():
    """유니코드 문자열 암호화/복호화."""
    plaintext = "한글 API 키 테스트 123"
    encrypted = encrypt_value(plaintext)
    decrypted = decrypt_value(encrypted)
    assert decrypted == plaintext


def test_encrypt_special_characters():
    """특수 문자가 포함된 문자열."""
    plaintext = "key!@#$%^&*()_+-=[]{}|;':\",./<>?~`"
    encrypted = encrypt_value(plaintext)
    decrypted = decrypt_value(encrypted)
    assert decrypted == plaintext


def test_encrypt_long_string():
    """긴 문자열 암호화/복호화 (4096자)."""
    plaintext = "A" * 4096
    encrypted = encrypt_value(plaintext)
    decrypted = decrypt_value(encrypted)
    assert decrypted == plaintext


# ──────────────────────────────────────────────
# 실패 케이스 테스트
# ──────────────────────────────────────────────

def test_decrypt_with_wrong_key():
    """다른 키로 복호화 시 ValueError 발생."""
    plaintext = "secret"
    encrypted = encrypt_value(plaintext)

    # 키 변경
    reset_fernet()
    new_key = Fernet.generate_key().decode()
    os.environ["ENCRYPTION_KEY"] = new_key

    with pytest.raises(ValueError, match="복호화 실패"):
        decrypt_value(encrypted)


def test_decrypt_corrupted_ciphertext():
    """변조된 암호문으로 복호화 시 ValueError 발생."""
    with pytest.raises((ValueError, Exception)):
        decrypt_value("this_is_not_a_valid_fernet_token_at_all")


def test_encryption_key_not_set_auto_generates():
    """ENCRYPTION_KEY 미설정 시 자동 생성되어 동작."""
    reset_fernet()
    if "ENCRYPTION_KEY" in os.environ:
        del os.environ["ENCRYPTION_KEY"]

    # 자동 키 생성으로 동작해야 함
    encrypted = encrypt_value("test")
    decrypted = decrypt_value(encrypted)
    assert decrypted == "test"

    # 환경변수에 키가 자동 설정되었는지 확인
    assert os.environ.get("ENCRYPTION_KEY") != ""


def test_invalid_encryption_key_auto_recovers():
    """잘못된 형식의 ENCRYPTION_KEY → 자동 복구."""
    reset_fernet()
    os.environ["ENCRYPTION_KEY"] = "this-is-not-a-valid-fernet-key"

    # 자동 복구되어 동작해야 함
    encrypted = encrypt_value("test_recover")
    decrypted = decrypt_value(encrypted)
    assert decrypted == "test_recover"


# ──────────────────────────────────────────────
# 보안 속성 확인
# ──────────────────────────────────────────────

def test_encrypted_value_not_contains_plaintext():
    """암호문에 평문이 포함되지 않음 (기본 보안 확인)."""
    plaintext = "my_super_secret_key"
    encrypted = encrypt_value(plaintext)
    assert plaintext not in encrypted


def test_reset_fernet_clears_cache():
    """reset_fernet 호출 후 캐시 초기화 확인."""
    encrypt_value("before_reset")
    reset_fernet()
    # 새 키 설정
    new_key = Fernet.generate_key().decode()
    os.environ["ENCRYPTION_KEY"] = new_key
    # 새 키로 동작해야 함
    encrypted = encrypt_value("after_reset")
    decrypted = decrypt_value(encrypted)
    assert decrypted == "after_reset"
