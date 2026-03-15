"""
Test module for frontend UI file serving.
"""
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def test_root_serves_index_html():
    """Verify the root endpoint serves the React index.html."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert '<div id="root"></div>' in response.text
    assert "unpkg.com/react" in response.text


def test_serves_react_app():
    """Verify the App.jsx React component is available."""
    response = client.get("/src/App.jsx")
    assert response.status_code == 200
    assert "function App()" in response.text
    assert "Deep Dive Chat" in response.text


def test_serves_stylesheet():
    """Verify the frontend stylesheet is served."""
    response = client.get("/style.css")
    assert response.status_code == 200
    assert "--bg-primary" in response.text
