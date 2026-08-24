"""Atomic writers for per-source CSV/JSON/TXT outputs and the manifest.

Address/JSON/TXT files never include ``retrieved_at``, ``resolved_url``, or any
other run-specific metadata -- only ``manifest.json`` carries volatile fields,
so identical source inputs produce byte-identical address files across runs.
"""

from __future__ import annotations

import contextlib
import csv
import io
import json
import os
import tempfile
from pathlib import Path

from sanctions_address_lists.models import SourceResult

CSV_HEADER = ("address", "jurisdiction", "source", "source_record_id", "source_url")


def _atomic_write(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` atomically: never leaves a partial file in place."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as tmp_file:
            tmp_file.write(data)
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.remove(tmp_name)
        raise


def _csv_bytes(result: SourceResult) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    # Deduplicate by (address, source_record_id, source_url) defensively, even
    # though SourceAdapter.run() already does this -- the CSV writer's output
    # contract holds regardless of what the caller passes in.
    deduped = {link.dedup_key: link for link in result.links}.values()
    for link in sorted(deduped, key=lambda link: link.sort_key):
        writer.writerow(
            (link.address, link.jurisdiction, link.source, link.source_record_id, link.source_url)
        )
    return buffer.getvalue().encode("utf-8")


def _json_bytes(result: SourceResult) -> bytes:
    addresses = sorted({link.address for link in result.links})
    return (json.dumps(addresses, indent=2) + "\n").encode("utf-8")


def _txt_bytes(result: SourceResult) -> bytes:
    addresses = sorted({link.address for link in result.links})
    body = "\n".join(addresses)
    return (body + "\n" if addresses else "").encode("utf-8")


def write_source_outputs(result: SourceResult, out_dir: Path) -> list[str]:
    """Write CSV/JSON/TXT outputs for a successful result; return relative file paths.

    Writes (and touches) nothing unless ``result.status == "success"`` -- a
    failed, unsupported, or unverified run leaves any prior good output for
    that source exactly as it was.
    """
    if result.status != "success":
        return []

    generated: list[str] = []
    for fmt, encoder in (("csv", _csv_bytes), ("json", _json_bytes), ("txt", _txt_bytes)):
        relative_path = f"{fmt}/{result.source_id}.{fmt}"
        _atomic_write(out_dir / relative_path, encoder(result))
        generated.append(relative_path)
    return generated


def manifest_entry(result: SourceResult, generated_files: list[str]) -> dict[str, object]:
    return {
        "source_id": result.source_id,
        "jurisdiction": result.jurisdiction,
        "source_url": result.source_url,
        "resolved_url": result.resolved_url,
        "retrieved_at": result.retrieved_at,
        "content_hash": result.content_hash,
        "status": result.status,
        "record_count": result.record_count,
        "address_count": result.address_count,
        "generated_files": generated_files,
        "error": result.error,
    }


def write_manifest(entries: list[dict[str, object]], out_dir: Path) -> None:
    payload = json.dumps(entries, indent=2) + "\n"
    _atomic_write(out_dir / "manifest.json", payload.encode("utf-8"))
