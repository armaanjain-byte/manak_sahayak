"""
Tests for the Action Router (app/actions/router.py).

Verifies that resolve_action correctly validates destinations against the
known official BIS URLs and attaches the right disclaimers.
"""
import pytest

from app.core.entities import Action
from app.actions.destinations import (
    BIS_CARE_APP_URL,
    BIS_HALLMARKING_INFO_URL,
    BIS_LIMS_URL,
    BIS_KNOW_YOUR_STANDARD_URL,
    BIS_MAIN_URL,
)
from app.actions.router import resolve_action, ResolvedAction, UnknownDestinationError


# ---------------------------------------------------------------------------
# Known action types → correct destinations and disclaimers
# ---------------------------------------------------------------------------

def test_resolve_action_huid_verification() -> None:
    """huid_verification action resolves to BIS CARE URL with HUID disclaimer."""
    action = Action(action_type="huid_verification", destination_url=BIS_CARE_APP_URL)
    resolved = resolve_action(action)

    assert isinstance(resolved, ResolvedAction)
    assert resolved.destination_url == BIS_CARE_APP_URL
    assert resolved.destination_name == "BIS CARE"
    assert "CARE" in resolved.disclaimer or "HUID" in resolved.disclaimer


def test_resolve_action_hallmarking_info() -> None:
    """hallmarking_info action resolves to hallmarking page with correct disclaimer."""
    action = Action(action_type="hallmarking_info", destination_url=BIS_HALLMARKING_INFO_URL)
    resolved = resolve_action(action)

    assert resolved.destination_url == BIS_HALLMARKING_INFO_URL
    assert resolved.destination_name == "BIS Hallmarking Information"
    assert "hallmarking" in resolved.disclaimer.lower()


def test_resolve_action_search_lims() -> None:
    """search_lims action resolves to LIMS URL with laboratory disclaimer."""
    action = Action(action_type="search_lims", destination_url=BIS_LIMS_URL)
    resolved = resolve_action(action)

    assert resolved.destination_url == BIS_LIMS_URL
    assert resolved.destination_name == "BIS LIMS Laboratory Search"
    assert "LIMS" in resolved.disclaimer or "laborator" in resolved.disclaimer.lower()


def test_resolve_action_know_your_standard() -> None:
    """know_your_standard action resolves to KYS URL."""
    action = Action(action_type="know_your_standard", destination_url=BIS_KNOW_YOUR_STANDARD_URL)
    resolved = resolve_action(action)

    assert resolved.destination_url == BIS_KNOW_YOUR_STANDARD_URL
    assert resolved.destination_name == "BIS Know Your Standard"


def test_resolve_action_general_bis_handoff() -> None:
    """general_bis_handoff resolves to main BIS site."""
    action = Action(action_type="general_bis_handoff", destination_url=BIS_MAIN_URL)
    resolved = resolve_action(action)

    assert resolved.destination_url == BIS_MAIN_URL
    assert resolved.destination_name == "BIS Official Website"


def test_resolve_action_unknown_action_type_gets_default_disclaimer() -> None:
    """An unknown action_type still resolves if the URL is known, using the default disclaimer."""
    action = Action(action_type="some_future_action", destination_url=BIS_CARE_APP_URL)
    resolved = resolve_action(action)
    assert resolved.destination_url == BIS_CARE_APP_URL
    # Should use the default disclaimer
    assert "official BIS" in resolved.disclaimer


# ---------------------------------------------------------------------------
# Unknown / invalid destinations → error
# ---------------------------------------------------------------------------

def test_resolve_action_rejects_unknown_url() -> None:
    """An action with an unrecognised destination URL raises UnknownDestinationError."""
    action = Action(
        action_type="general_bis_handoff",
        destination_url="https://suspicious-third-party.example.com/"
    )
    with pytest.raises(UnknownDestinationError):
        resolve_action(action)


def test_resolve_action_rejects_empty_url() -> None:
    """An action with an empty destination URL raises UnknownDestinationError."""
    with pytest.raises(Exception):
        action = Action(action_type="general_bis_handoff", destination_url="")
        resolve_action(action)
