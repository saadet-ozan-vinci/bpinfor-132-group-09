"""Exception types used by the Week 8 retry ladder."""

from __future__ import annotations


class ToolTimeout(Exception):
    """The call did not return in time."""


class RateLimited(Exception):
    """The upstream returned a retryable 429."""


class ServerError(Exception):
    """The upstream returned a retryable 5xx."""


class ContractDrift(Exception):
    """The call succeeded but the response violated its contract."""
