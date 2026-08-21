"""Adapter-level errors distinguishing structural failure from a valid empty result."""

from __future__ import annotations


class SchemaError(Exception):
    """The retrieved dataset's structure doesn't match what the adapter expects."""


class EmptyResultError(Exception):
    """The dataset parsed to zero records (a valid source may still yield zero addresses)."""
