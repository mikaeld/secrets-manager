import json
import pytest
from unittest.mock import Mock, patch
from secrets_manager.utils.gcp import (
    list_secrets,
    get_secret_versions,
    get_secret_version_value,
    search_gcp_projects
)
from secrets_manager.models.gcp_projects import GCPProject


@pytest.fixture
def mock_secret_manager_client():
    with patch('google.cloud.secretmanager.SecretManagerServiceClient') as mock:
        yield mock


@pytest.fixture
def mock_projects_client():
    with patch('google.cloud.resourcemanager_v3.ProjectsClient') as mock:
        yield mock


def test_list_secrets(mock_secret_manager_client):
    mock_project = GCPProject(
        name="projects/123",
        project_id="test-project",
        display_name="Test Project"
    )

    mock_client = Mock()
    mock_secret_manager_client.return_value = mock_client
    mock_client.list_secrets.return_value = []

    result = list_secrets(mock_project)

    mock_client.list_secrets.assert_called_once_with(
        request={"parent": f"projects/{mock_project.project_id}"}
    )


def test_get_secret_versions(mock_secret_manager_client, mock_secret):
    mock_client = Mock()
    mock_secret_manager_client.return_value = mock_client
    mock_client.list_secret_versions.return_value = []

    # Test without deleted versions
    result = get_secret_versions(mock_secret)

    # Verify that list_secret_versions was called once
    assert mock_client.list_secret_versions.called
    # Get the actual call arguments
    call_args = mock_client.list_secret_versions.call_args[1]['request']
    # Verify the request parameters individually
    assert call_args.parent == mock_secret.name
    assert call_args.filter == "state!=DESTROYED"

    # Test with deleted versions
    mock_client.list_secret_versions.reset_mock()
    result = get_secret_versions(mock_secret, show_deleted=True)

    # Verify the call for show_deleted=True
    assert mock_client.list_secret_versions.called
    call_args = mock_client.list_secret_versions.call_args[1]['request']
    assert call_args.parent == mock_secret.name


def test_get_secret_version_value(mock_secret_manager_client, mock_secret_version):
    mock_client = Mock()
    mock_secret_manager_client.return_value = mock_client

    mock_response = Mock()
    mock_response.payload.data = json.dumps({"key": "value"}).encode()
    mock_client.access_secret_version.return_value = mock_response

    result = get_secret_version_value(mock_secret_version)

    assert result == {"key": "value"}
    mock_client.access_secret_version.assert_called_once_with(
        request={"name": mock_secret_version.name}
    )


def test_search_gcp_projects(mock_projects_client):
    mock_client = Mock()
    mock_projects_client.return_value = mock_client

    mock_project = Mock()
    mock_project.name = "projects/123"
    mock_project.project_id = "test-project"
    mock_project.display_name = "Test Project"
    mock_project.parent = "organizations/456"
    mock_project.labels = {}

    mock_client.search_projects.return_value = [mock_project]

    result = search_gcp_projects("test")

    assert len(result) == 1
    assert isinstance(result[0], GCPProject)
    assert result[0].project_id == "test-project"

    mock_client.search_projects.assert_called_once()
