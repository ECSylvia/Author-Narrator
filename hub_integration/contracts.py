"""Boundary contracts between Doxie Hub and Author Narrator."""
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class HubPrincipal:
    subject: str
    workspace_id: str
    email: str | None = None

@dataclass(frozen=True)
class HubProjectContext:
    hub_project_id: str
    workspace_id: str
    product_slug: str = "author-narrator"

class HubVerifier(Protocol):
    async def verify_session(self, credential: str) -> HubPrincipal: ...
    async def has_entitlement(self, principal: HubPrincipal, entitlement: str) -> bool: ...

class VoiceEngine(Protocol):
    """Voice synthesis implementation belongs to the independent engine workstream."""
    async def generate_preview(self, *, voice_profile_id: str, text: str) -> bytes: ...
    async def generate_chapter(self, *, voice_profile_id: str, text: str) -> bytes: ...
