import os
import json
import time
from datetime import datetime

class Project:
    def __init__(self, name, path, created_at=None, modified_at=None):
        self.name = name
        self.path = path
        self.created_at = created_at or datetime.now().isoformat()
        self.modified_at = modified_at or datetime.now().isoformat()
        
    def to_dict(self):
        return {
            "name": self.name,
            "created_at": self.created_at,
            "modified_at": self.modified_at
        }
        
    @classmethod
    def from_dict(cls, data, path):
        return cls(
            name=data["name"],
            path=path,
            created_at=data.get("created_at"),
            modified_at=data.get("modified_at")
        )
        
    def save(self):
        # Update modified time
        self.modified_at = datetime.now().isoformat()
        
        # Ensure directory exists
        if not os.path.exists(self.path):
            os.makedirs(self.path)
            
        # Create subdirectories if they don't exist
        os.makedirs(os.path.join(self.path, "manuscript"), exist_ok=True)
        os.makedirs(os.path.join(self.path, "audio"), exist_ok=True)
        
        # Save project.json
        project_file = os.path.join(self.path, "project.json")
        with open(project_file, 'w') as f:
            json.dump(self.to_dict(), f, indent=4)

class ProjectManager:
    @staticmethod
    def create_project(name, base_directory, overwrite=False):
        """Creates a new project in the specified directory."""
        # Sanitize name for folder usage
        safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        project_path = os.path.join(base_directory, safe_name)
        
        if os.path.exists(project_path):
            if overwrite:
                import shutil
                try:
                    shutil.rmtree(project_path)
                except Exception as e:
                    raise IOError(f"Failed to overwrite project: {e}")
            else:
                raise ValueError(f"Project '{name}' already exists in this location.")
            
        project = Project(name, project_path)
        project.save()
        return project

    @staticmethod
    def load_project(project_path):
        """Loads a project from a directory."""
        info_path = os.path.join(project_path, "project.json")
        if not os.path.exists(info_path):
            raise ValueError("Not a valid Author Narrator project (missing project.json)")
            
        with open(info_path, 'r') as f:
            data = json.load(f)
            
        return Project.from_dict(data, project_path)
