import pytest
from google.cloud.resourcemanager_v3.types import Project
from google.cloud import secretmanager

@pytest.fixture
def mock_project_data():
    return {
        "name": "projects/123456789",
        "project_id": "test-project-123",
        "display_name": "Test Project",
        "parent": "organizations/456",
        "labels": {"environment": "test", "team": "platform"}
    }

@pytest.fixture
def mock_gcp_project(mock_project_data):
    return Project(
        name=mock_project_data["name"],
        project_id=mock_project_data["project_id"],
        display_name=mock_project_data["display_name"],
        parent=mock_project_data["parent"],
        labels=mock_project_data["labels"]
    )

@pytest.fixture
def mock_secret():
    return secretmanager.Secret(
        name="projects/123456789/secrets/test-secret"
    )

@pytest.fixture
def mock_secret_version():
    return secretmanager.SecretVersion(
        name="projects/123456789/secrets/test-secret/versions/1"
    )