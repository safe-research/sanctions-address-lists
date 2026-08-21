import logging

import pytest

from sanctions_address_lists.textscan import scan_text_fields

ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"


def test_extracts_address_embedded_in_prose() -> None:
    text = f"Known blockchain wallet addresses: {ADDRESS} (last active 2024)."
    assert scan_text_fields([text], record_id="r1", source_id="test") == [ADDRESS]


def test_normalizes_to_lowercase() -> None:
    text = f"Address: {ADDRESS.upper()}"
    assert scan_text_fields([text], record_id="r1", source_id="test") == [ADDRESS]


def test_ignores_40_hex_substring_inside_64_hex_hash() -> None:
    tx_hash = "0x" + "ab" * 32
    assert scan_text_fields([tx_hash], record_id="r1", source_id="test") == []


def test_ignores_39_char_near_miss() -> None:
    short = "0x" + "1" * 39
    assert scan_text_fields([short], record_id="r1", source_id="test") == []


def test_ignores_41_char_near_miss() -> None:
    long_ = "0x" + "1" * 41
    assert scan_text_fields([long_], record_id="r1", source_id="test") == []


def test_skips_none_and_empty_texts() -> None:
    assert scan_text_fields([None, "", "no address here"], record_id="r1", source_id="test") == []


def test_deduplicates_within_and_across_texts() -> None:
    result = scan_text_fields(
        [f"{ADDRESS} and again {ADDRESS}", ADDRESS], record_id="r1", source_id="test"
    )
    assert result == [ADDRESS]


def test_keyword_not_required_for_extraction() -> None:
    # No crypto-related keyword anywhere nearby -- extraction still happens.
    text = f"Mother's maiden name was Wallet Sidi, unrelated to {ADDRESS}."
    assert scan_text_fields([text], record_id="r1", source_id="test") == [ADDRESS]


def test_keyword_proximity_is_logged_not_required(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG, logger="sanctions_address_lists.textscan"):
        scan_text_fields(
            [f"Known crypto wallet address: {ADDRESS}"], record_id="r1", source_id="test"
        )
    assert any("keyword_nearby=True" in message for message in caplog.messages)
