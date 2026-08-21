"""Opt-in tests against live government endpoints.

Excluded by default (see `addopts` in pyproject.toml). Run explicitly with:

    pytest -m integration

These hit real, rate-limited government infrastructure -- do not run them in
a tight loop, and do not add them to the default CI test run.
"""

from __future__ import annotations

import pytest

from sanctions_address_lists.http import build_client
from sanctions_address_lists.sources.base import SourceAdapter
from sanctions_address_lists.sources.eu import EuAdapter
from sanctions_address_lists.sources.ofac import OfacAdapter
from sanctions_address_lists.sources.seco import SecoAdapter
from sanctions_address_lists.sources.uk import UkAdapter
from sanctions_address_lists.sources.un import UnAdapter

pytestmark = pytest.mark.integration


def test_ofac_live_run_succeeds_with_real_addresses() -> None:
    with build_client(timeout=60.0) as client:
        result = OfacAdapter().run(client)
    assert result.status == "success"
    assert result.record_count > 1000
    assert result.address_count > 0


@pytest.mark.parametrize("adapter_cls", [EuAdapter, UkAdapter, UnAdapter, SecoAdapter])
def test_structurally_confirmed_sources_run_successfully(
    adapter_cls: type[SourceAdapter],
) -> None:
    # SECO (sesam.search.admin.ch) has intermittently timed out at the TCP
    # level from some networks -- see FEASIBILITY.md. A failure here for
    # SecoAdapter specifically may be that known connectivity issue rather
    # than a code or schema regression; check that history before assuming
    # the adapter broke.
    with build_client(timeout=60.0) as client:
        result = adapter_cls().run(client)
    assert result.status == "success", result.error
    assert result.record_count > 0
