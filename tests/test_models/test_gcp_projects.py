import pytest
from secrets_manager.models.gcp_projects import GCPProject

def test_gcp_project_creation(mock_project_data):
    project = GCPProject(**mock_project_data)
    assert project.name == mock_project_data["name"]
    assert project.project_id == mock_project_data["project_id"]
    assert project.display_name == mock_project_data["display_name"]
    assert project.labels == mock_project_data["labels"]

def test_gcp_project_from_api_response(mock_gcp_project):
    project = GCPProject.from_project_api_response(mock_gcp_project)
    assert project.name == mock_gcp_project.name
    assert project.project_id == mock_gcp_project.project_id
    assert project.display_name == mock_gcp_project.display_name

def test_project_id_validation():
    with pytest.raises(ValueError):
        GCPProject(
            name="projects/123",
            project_id="123invalid",  # Must start with letter
            display_name="Test Project"
        )

def test_display_name_validation():
    with pytest.raises(ValueError):
        GCPProject(
            name="projects/123",
            project_id="valid-project",
            display_name="abc"  # Too short
        )

def test_labels_validation():
    # Test valid labels
    project = GCPProject(
        name="projects/123",
        project_id="valid-project",
        display_name="Valid Project",
        labels={"env": "test", "team-name": "platform"}
    )
    assert project.labels == {"env": "test", "team-name": "platform"}

    # Test invalid label key
    with pytest.raises(ValueError):
        GCPProject(
            name="projects/123",
            project_id="valid-project",
            display_name="Valid Project",
            labels={"invalid@key": "value"}
        )

    # Test invalid label value
    with pytest.raises(ValueError):
        GCPProject(
            name="projects/123",
            project_id="valid-project",
            display_name="Valid Project",
            labels={"key": "invalid@value"}
        )

def test_string_representation(mock_project_data):
    project = GCPProject(**mock_project_data)
    str_repr = str(project)
    assert project.display_name in str_repr
    assert project.name in str_repr
    assert project.project_id in str_repr
