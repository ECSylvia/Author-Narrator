"""Fail-closed authorization for future hosted integrations."""
from dataclasses import dataclass
from .contracts import HubPrincipal, HubProjectContext

REQUIRED_ENTITLEMENT = "author_narrator.access"

@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason: str

def check_project_context(principal: HubPrincipal, project: HubProjectContext,
                          entitled: bool) -> AccessDecision:
    if project.product_slug != "author-narrator":
        return AccessDecision(False, "Incorrect product")
    if not principal.subject or not principal.workspace_id:
        return AccessDecision(False, "Unverified principal")
    if principal.workspace_id != project.workspace_id:
        return AccessDecision(False, "Workspace mismatch")
    if not entitled:
        return AccessDecision(False, "Missing entitlement")
    return AccessDecision(True, "Authorized")

def mock_identity_is_disabled_in_production(environment: str, auth_mode: str) -> bool:
    return not (environment.lower() in {"production", "staging"} and auth_mode == "mock")
