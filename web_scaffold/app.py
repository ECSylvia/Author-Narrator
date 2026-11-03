"""Author Narrator web integration stub. Not production authentication."""
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel, Field
from src.core.manuscript_parser import ManuscriptParser
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

class ManuscriptPreviewRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=2_000_000)

@app.post("/manuscripts/preview")
def preview_manuscript(payload: ManuscriptPreviewRequest):
    # Stateless text preview only. No file writes or customer project creation.
    # Never accept arbitrary server-side file paths from browser requests.
    ext = payload.filename.rsplit(".", 1)[-1].lower() if "." in payload.filename else ""
    if ext not in ("md", "txt"):
        raise HTTPException(status_code=415, detail="Only .md and .txt manuscripts are supported")
    parser = ManuscriptParser._parse_markdown if ext == "md" else ManuscriptParser._parse_text
    chapters = parser(payload.content)
    return {"chapters": [
        {"title": chapter.title, "order": chapter.order, "characters": len(chapter.content)}
        for chapter in chapters
    ], "count": len(chapters)}

@app.get("/studio", include_in_schema=False)
def studio():
    return FileResponse(Path(__file__).resolve().parent / "static" / "index.html")
