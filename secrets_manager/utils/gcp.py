import json

from google.cloud import resourcemanager_v3, secretmanager
from google.cloud.secretmanager_v1.services.secret_manager_service.pagers import (
    ListSecretsPager,
)

from secrets_manager.models.gcp_projects import GCPProject


def list_secrets(gcp_project: GCPProject) -> ListSecretsPager:
    """
    List all secrets in a GCP project.

    Args:
        gcp_project (GCPProject): The GCP project to list secrets from

    Returns:
        ListSecretsPager: Paginated list of secrets
    """
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
    request = secretmanager.ListSecretVersionsRequest(
        parent=secret.name, filter="state!=DESTROYED" if not show_deleted else None
    )

    return list(client.list_secret_versions(request=request))


def get_secret_version_value(secret_id: str) -> dict:
    """
    Get the value of a specific secret version.

    Args:
        secret_id (str): Secret identifier in the format "projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

    Returns:
        dict: The decoded secret value
    """
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(request={"name": secret_id})
    return json.loads(response.payload.data)


def search_gcp_projects(search_term: str) -> list[GCPProject]:
    """
    Search for GCP projects that partially match the given search term.

    Args:
        search_term (str): The partial name to search for in project names/IDs

    Returns:
        List[GCPProject]: List of matching projects as Pydantic models

    Raises:
        Exception: If project search fails
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


def add_secret_version(secret_id: str, payload: dict) -> secretmanager.SecretVersion:
    """
    Add a new version to an existing secret in GCP Secret Manager.

    Args:
        secret_id (str): Parent secret path in format "projects/{project_id}/secrets/{secret_id}"
        payload (dict): The secret data to store as a dictionary

    Returns:
        secretmanager.SecretVersion: The newly created secret version
    """
    client = secretmanager.SecretManagerServiceClient()
    secret_data = json.dumps(payload).encode("UTF-8")

    request = secretmanager.AddSecretVersionRequest(
        parent=secret_id,
        payload={"data": secret_data},
    )

    return client.add_secret_version(request=request)
