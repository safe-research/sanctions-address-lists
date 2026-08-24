import json
from pathlib import Path

import pytest

from sanctions_address_lists.models import AddressLink, SourceResult
from sanctions_address_lists.output import manifest_entry, write_manifest, write_source_outputs

ADDR_A = "0x1111111111111111111111111111111111111111"
ADDR_B = "0x2222222222222222222222222222222222222222"


def _result(**overrides: object) -> SourceResult:
    defaults: dict[str, object] = {
        "source_id": "us-ofac",
        "jurisdiction": "US",
        "source_url": "https://example.org/sdn.xml",
        "status": "success",
        "resolved_url": "https://example.org/sdn.xml",
        "retrieved_at": "2026-08-20T00:00:00+00:00",
        "content_hash": "abc123",
        "record_count": 2,
        "links": (
            AddressLink(ADDR_B, "US", "us-ofac", "rec-2", "https://example.org/sdn.xml"),
            AddressLink(ADDR_A, "US", "us-ofac", "rec-1", "https://example.org/sdn.xml"),
            # Same address+record+url repeated -- must be deduplicated by the caller
            # before reaching output writers (mirrors what SourceAdapter.run() does).
            AddressLink(ADDR_A, "US", "us-ofac", "rec-1", "https://example.org/sdn.xml"),
            # Same address, different record -- retained as a distinct CSV row.
            AddressLink(ADDR_A, "US", "us-ofac", "rec-3", "https://example.org/sdn.xml"),
        ),
    }
    defaults.update(overrides)
    return SourceResult(**defaults)  # type: ignore[arg-type]


def test_csv_sorted_by_address_then_record_id_and_retains_multi_record_rows(
    tmp_path: Path,
) -> None:
    result = _result()
    write_source_outputs(result, tmp_path)
    csv_text = (tmp_path / "csv" / "us-ofac.csv").read_text()
    lines = csv_text.strip("\n").split("\n")
    assert lines[0] == "address,jurisdiction,source,source_record_id,source_url"
    # rec-1 duplicate collapses; rec-1 and rec-3 for ADDR_A both retained (distinct records).
    assert lines[1:] == [
        f"{ADDR_A},US,us-ofac,rec-1,https://example.org/sdn.xml",
        f"{ADDR_A},US,us-ofac,rec-3,https://example.org/sdn.xml",
        f"{ADDR_B},US,us-ofac,rec-2,https://example.org/sdn.xml",
    ]


def test_json_is_sorted_deduplicated_address_array(tmp_path: Path) -> None:
    result = _result()
    write_source_outputs(result, tmp_path)
    data = json.loads((tmp_path / "json" / "us-ofac.json").read_text())
    assert data == [ADDR_A, ADDR_B]


def test_txt_is_sorted_deduplicated_one_per_line(tmp_path: Path) -> None:
    result = _result()
    write_source_outputs(result, tmp_path)
    lines = (tmp_path / "txt" / "us-ofac.txt").read_text().strip("\n").split("\n")
    assert lines == [ADDR_A, ADDR_B]


def test_empty_links_produce_empty_but_valid_outputs(tmp_path: Path) -> None:
    result = _result(links=(), record_count=5)
    generated = write_source_outputs(result, tmp_path)
    assert generated == ["csv/us-ofac.csv", "json/us-ofac.json", "txt/us-ofac.txt"]
    assert json.loads((tmp_path / "json" / "us-ofac.json").read_text()) == []
    # Never a literal 0-byte file -- GitHub's release-asset upload API rejects
    # those outright, and CSV/JSON are never 0 bytes either (header/"[]").
    txt_path = tmp_path / "txt" / "us-ofac.txt"
    assert txt_path.read_text() == "\n"
    assert txt_path.stat().st_size > 0


@pytest.mark.parametrize("status", ["failed", "unsupported", "unverified"])
def test_non_success_statuses_write_nothing(tmp_path: Path, status: str) -> None:
    result = _result(status=status)
    generated = write_source_outputs(result, tmp_path)
    assert generated == []
    assert not (tmp_path / "csv" / "us-ofac.csv").exists()


def test_failed_run_does_not_clobber_prior_good_output(tmp_path: Path) -> None:
    good = _result(status="success")
    write_source_outputs(good, tmp_path)
    before = (tmp_path / "csv" / "us-ofac.csv").read_text()

    failing = _result(status="failed", links=(), error="boom")
    generated = write_source_outputs(failing, tmp_path)

    assert generated == []
    after = (tmp_path / "csv" / "us-ofac.csv").read_text()
    assert after == before


def test_reproducibility_identical_addresses_different_volatile_fields(tmp_path: Path) -> None:
    run1_dir = tmp_path / "run1"
    run2_dir = tmp_path / "run2"
    result1 = _result(retrieved_at="2026-08-20T00:00:00+00:00", resolved_url="https://a")
    result2 = _result(retrieved_at="2027-01-01T12:34:56+00:00", resolved_url="https://b")

    write_source_outputs(result1, run1_dir)
    write_source_outputs(result2, run2_dir)

    for fmt in ("csv", "json", "txt"):
        content1 = (run1_dir / fmt / f"us-ofac.{fmt}").read_bytes()
        content2 = (run2_dir / fmt / f"us-ofac.{fmt}").read_bytes()
        assert content1 == content2


def test_manifest_entry_fields_and_generated_files_empty_when_not_success() -> None:
    result = _result(status="unverified", error="pending live verification")
    entry = manifest_entry(result, generated_files=[])
    assert entry["source_id"] == "us-ofac"
    assert entry["status"] == "unverified"
    assert entry["generated_files"] == []
    assert entry["resolved_url"] == "https://example.org/sdn.xml"
    assert entry["error"] == "pending live verification"
    assert entry["address_count"] == 2


def test_write_manifest_is_a_json_array(tmp_path: Path) -> None:
    result = _result()
    entry = manifest_entry(result, write_source_outputs(result, tmp_path))
    write_manifest([entry], tmp_path)
    data = json.loads((tmp_path / "manifest.json").read_text())
    assert isinstance(data, list)
    assert data[0]["source_id"] == "us-ofac"
    assert data[0]["generated_files"] == ["csv/us-ofac.csv", "json/us-ofac.json", "txt/us-ofac.txt"]
