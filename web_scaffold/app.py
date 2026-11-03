"""Author Narrator web integration stub. Not production authentication."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from hub_integration.security import REQUIRED_ENTITLEMENT

app = FastAPI(title="Author Narrator Hub Adapter", version="0.1.0")

class ProjectLaunchRequest(BaseModel):
    hub_project_id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)

@app.get("/health")
def health():
    return {"ok": True, "product": "author-narrator", "version": "0.1.0"}

@app.get("/integration")
def integration():
    return {"hub_managed_identity": True, "hub_managed_billing": True,
            "required_entitlement": REQUIRED_ENTITLEMENT,
            "live_session_verification": False,
            "voice_engine": "not_connected"}

@app.post("/launch")
def launch(payload: ProjectLaunchRequest):
    # A browser-supplied workspace or project ID is never proof of authorization.
    raise HTTPException(status_code=501, detail="Hub session and entitlement verification not yet connected")
