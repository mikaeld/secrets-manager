from google.cloud.resourcemanager_v3.types import Project
from pydantic import BaseModel, Field, field_validator


class GCPProject(BaseModel):
    """
    Pydantic model representing a Google Cloud Platform project.
    """

    name: str = Field(
        description="The unique resource name of the project (e.g., projects/415104041262)"
    )
    parent: str | None = Field(
        default=None,
        description="Reference to parent resource (e.g., organizations/123 or folders/876)",
    )
    project_id: str = Field(
        description="Unique, user-assigned project ID",
        pattern=r"^[a-z][a-z0-9-]{5,29}$",
        # 6-30 chars, starts with letter, no trailing hyphen
    )
    display_name: str = Field(
        min_length=4,
        max_length=30,
        description="User-assigned display name of the project",
    )
    labels: dict[str, str] = Field(
        default_factory=dict, description="Key-value pairs for project labels"
    )

    @staticmethod
    def from_project_api_response(project: Project) -> "GCPProject":
        """
        Creates a GCPProject instance from a search response Project object.

        Args:
            project: Project object from the Google Cloud Resource Manager API

        Returns:
            GCPProject: A validated Pydantic model instance
        """
        return GCPProject(
            name=project.name,
            parent=project.parent,
            project_id=project.project_id,
            display_name=project.display_name,
            labels=dict(project.labels),
        )

    def __str__(self):
        """String representation of the GCPProject instance."""
        return f"GCPProject(display_name={self.display_name}, name={self.name}, project_id={self.project_id})"

    @field_validator("labels")
    def validate_labels(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate label keys and values according to GCP requirements."""
        for key, value in v.items():
            # Validate key format
            if not key.isalnum() and not all(c in "-_" for c in key if not c.isalnum()):
                raise ValueError(f"Invalid label key format: {key}")
            if len(key) > 63:
                raise ValueError(f"Label key too long: {key}")

            # Validate value format
            if not value.isalnum() and not all(c in "-_" for c in value if not c.isalnum()):
                raise ValueError(f"Invalid label value format: {value}")
            if len(value) > 63:
                raise ValueError(f"Label value too long: {value}")

        if len(v) > 64:
            raise ValueError("Too many labels (maximum is 64)")

        return v

    class ConfigDict:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "name": "projects/123456789",
                "project_id": "my-project-123",
                "display_name": "My Project",
                "state": "ACTIVE",
                "labels": {"environment": "production", "team": "platform"},
            }
        }
