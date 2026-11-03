"""Local project metadata adapter. Does not rewrite existing project files."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass(frozen=True)
class ProjectLink:
    hub_project_id: str
    workspace_id: str
    local_project_path: str

def read_link(link_file: Path) -> ProjectLink:
    data = json.loads(link_file.read_text(encoding="utf-8"))
    return ProjectLink(**data)

def link_metadata(project: ProjectLink) -> dict:
    """Metadata for later storage; caller must validate authorization first."""
    return {"hub_project_id": project.hub_project_id,
            "workspace_id": project.workspace_id,
            "local_project_path": project.local_project_path}
