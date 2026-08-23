"""
Action Router.

Given an Action from a WorkflowResult, validates the destination URL
against the known official BIS constants and attaches a standardised
disclaimer before it is surfaced to the user.
"""
from dataclasses import dataclass

from app.core.entities import Action
from app.actions.destinations import (
    BIS_CARE_APP_URL,
    BIS_HALLMARKING_INFO_URL,
    BIS_LIMS_URL,
    BIS_KNOW_YOUR_STANDARD_URL,
    BIS_MAIN_URL,
)

# Set of all known, authorised BIS destination URLs.
# Any action pointing outside this set is an error.
_KNOWN_DESTINATIONS: dict[str, str] = {
    BIS_CARE_APP_URL: "BIS CARE",
    BIS_HALLMARKING_INFO_URL: "BIS Hallmarking Information",
    BIS_LIMS_URL: "BIS LIMS Laboratory Search",
    BIS_KNOW_YOUR_STANDARD_URL: "BIS Know Your Standard",
    BIS_MAIN_URL: "BIS Official Website",
}

_DISCLAIMERS: dict[str, str] = {
    "huid_verification": (
        "You are being redirected to the official BIS CARE portal for HUID verification. "
        "Do not share sensitive credentials with third-party services."
    ),
    "hallmarking_info": (
        "You are being redirected to the official BIS hallmarking information page."
    ),
    "search_lims": (
        "You are being redirected to the BIS Laboratory Information Management System (LIMS) "
        "to find NABL-accredited and BIS-recognised testing laboratories."
    ),
    "know_your_standard": (
        "You are being redirected to the official BIS 'Know Your Standard' portal."
    ),
    "general_bis_handoff": (
        "You are being redirected to the official Bureau of Indian Standards website."
    ),
}

_DEFAULT_DISCLAIMER = "You are being redirected to an official BIS portal."


@dataclass(frozen=True)
class ResolvedAction:
    """The resolved action ready for the API response."""
    action_type: str
    destination_url: str
    destination_name: str
    disclaimer: str


class UnknownDestinationError(ValueError):
    """Raised when an Action points to an unrecognised destination URL."""
    pass


def resolve_action(action: Action) -> ResolvedAction:
    """
    Validate and enrich an Action for API response.

    Args:
        action: The Action from a WorkflowResult.

    Returns:
        A ResolvedAction with the validated URL, destination name, and disclaimer.

    Raises:
        UnknownDestinationError: If the action's destination_url is not in
            the authorised set of BIS destinations.
    """
    destination_name = _KNOWN_DESTINATIONS.get(action.destination_url)
    if destination_name is None:
        raise UnknownDestinationError(
            f"Action destination '{action.destination_url}' is not a known "
            f"official BIS destination. Only pre-approved BIS URLs are permitted."
        )

    disclaimer = _DISCLAIMERS.get(action.action_type, _DEFAULT_DISCLAIMER)

    return ResolvedAction(
        action_type=action.action_type,
        destination_url=action.destination_url,
        destination_name=destination_name,
        disclaimer=disclaimer,
    )
