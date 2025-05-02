import json

from google.cloud import resourcemanager_v3, secretmanager
from google.cloud.secretmanager_v1.services.secret_manager_service.pagers import (
    ListSecretsPager,
)

from secrets_manager.models.gcp_projects import GCPProject


def list_secrets(gcp_project: GCPProject) -> ListSecretsPager:
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{gcp_project.project_id}"
    return client.list_secrets(request={"parent": parent})


def get_secret_versions(
    secret: secretmanager.Secret, show_deleted: bool = False
) -> list[secretmanager.SecretVersion]:
    """
    Get all versions of a secret from GCP Secret Manager.

    Args:
        secret (Secret): Secret instance to retrieve versions for
        show_deleted (bool, optional): Whether to include deleted versions. Defaults to False.

    Returns:
        List[secretmanager.SecretVersion]: List of secret versions
    """
    client = secretmanager.SecretManagerServiceClient()
    parent = secret.name

    # List all versions of the secret
    request = secretmanager.ListSecretVersionsRequest(
        parent=parent, filter="state!=DESTROYED" if not show_deleted else None
    )

    versions = []
    for version in client.list_secret_versions(request=request):
        versions.append(version)

    return versions


def get_secret_version_value(secret_id: str) -> dict:
    """
    Get the value of a specific secret version.

    Args:
        secret_id (str): Secret identifier in the format "projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

    Returns:
        str: The secret value
    """
    client = secretmanager.SecretManagerServiceClient()

    # Access the secret version
    response = client.access_secret_version(request={"name": secret_id})

    # Return the decoded payload
    return json.loads(response.payload.data)


def search_gcp_projects(search_term: str) -> list[GCPProject]:
    """
    Search for GCP projects that partially match the given search term.
    Returns results as validated Pydantic models.

    Args:
        search_term (str): The partial name to search for in project names/IDs

    Returns:
        List[GCPProject]: List of matching projects as Pydantic models
    """
    client = resourcemanager_v3.ProjectsClient()

    request = resourcemanager_v3.SearchProjectsRequest(
        query=f"projectId:*{search_term}* OR displayName:*{search_term}*"
    )

    try:
        projects = client.search_projects(request=request)
        return [GCPProject.from_project_api_response(project) for project in projects]

    except Exception as e:
        print(f"Error searching projects: {e}")
        raise
