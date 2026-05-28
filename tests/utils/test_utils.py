from datetime import datetime

from app.utils import decrypt_text, encrypt_text, normalize_date_range


def test_encrypt_and_decrypt_text():
    original = "Sensitive summary content."
    encrypted = encrypt_text(original)
    assert encrypted != original
    assert decrypt_text(encrypted) == original


def test_normalize_date_range_defaults():
    start, end = normalize_date_range(None, None)
    assert isinstance(start, datetime)
    assert isinstance(end, datetime)
    assert start < end


def test_normalize_date_range_rejects_invalid_range():
    start = datetime(2025, 1, 2)
    end = datetime(2025, 1, 1)
    try:
        normalize_date_range(start, end)
    except ValueError as exc:
        assert "start_date must be before end_date" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid range")
