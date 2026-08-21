from sanctions_address_lists.normalize import normalize_address

VALID = "0x1234567890abcdef1234567890ABCDEF12345678"
TX_HASH = "0x" + "ab" * 32  # 64 hex chars, looks like a transaction hash


def test_valid_address_normalizes_to_lowercase() -> None:
    assert normalize_address(VALID) == VALID.lower()


def test_strips_surrounding_whitespace() -> None:
    assert normalize_address(f"  {VALID}  ") == VALID.lower()


def test_rejects_none() -> None:
    assert normalize_address(None) is None


def test_rejects_empty_string() -> None:
    assert normalize_address("") is None


def test_rejects_too_short() -> None:
    assert normalize_address("0x1234567890abcdef1234567890ABCDEF1234567") is None


def test_rejects_too_long() -> None:
    assert normalize_address(TX_HASH) is None


def test_rejects_missing_0x_prefix() -> None:
    assert normalize_address("1234567890abcdef1234567890ABCDEF12345678") is None


def test_rejects_non_hex_characters() -> None:
    assert normalize_address("0x1234567890ZZZZef1234567890ABCDEF12345678") is None


def test_rejects_substring_match_inside_longer_value() -> None:
    # fullmatch must reject a value that merely *contains* a valid address.
    assert normalize_address(f"prefix {VALID} suffix") is None
