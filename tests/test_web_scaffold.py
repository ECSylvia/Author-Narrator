from fastapi.testclient import TestClient
from web_scaffold.app import app
client = TestClient(app)

def test_manuscript_preview_markdown():
    result = client.post("/manuscripts/preview", json={
        "filename":"story.md","content":"# Chapter One\nHello.\n# Chapter Two\nGoodbye."})
    assert result.status_code == 200
    assert result.json()["count"] == 2

def test_manuscript_preview_rejects_unsupported_file():
    assert client.post("/manuscripts/preview",json={
        "filename":"secret.exe","content":"x"}).status_code == 415

def test_launch_fails_closed():
    assert client.post("/launch",json={
        "hub_project_id":"p1","workspace_id":"w1"}).status_code == 501
