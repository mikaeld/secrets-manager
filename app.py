import json
import os
import pathlib
import tempfile
from json import JSONDecodeError

from google.api_core.exceptions import GoogleAPICallError
from google.cloud import secretmanager
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, Tree

from secrets_manager.models.gcp_projects import GCPProject
from secrets_manager.preview import SecretPreview
from secrets_manager.utils.gcp import (
    add_secret_version,
    get_secret_version_value,
    get_secret_versions,
    list_secrets,
    search_gcp_projects,
)
from secrets_manager.utils.helpers import (
    format_error_message,
    sanitize_project_id_search,
    shasum,
    validate_json_content,
)


class SecretsManager(App):
    """Main application class for the Secrets Manager TUI."""

    CSS_PATH = "secrets_manager.tcss"
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("p", "secret_preview", "Secret Preview"),
        Binding("e", "edit_secret", "Edit Secret"),
    ]
    EDITOR = os.getenv("EDITOR", "vi")

    search_query = reactive("")
    current_project: reactive[GCPProject | None] = reactive(None)

    def __init__(self) -> None:
        """Initialize the SecretsManager application."""
        super().__init__()
        self.client = secretmanager.SecretManagerServiceClient()

    def compose(self) -> ComposeResult:
        """Create and arrange the application widgets."""
        yield Header()
        yield Input(
            placeholder="Search by project ID or display name...",
            id="project-input-search",
        )

        with Horizontal(id="main-container"):
            yield Tree("Projects", id="projects-tree")
            with Vertical(id="secrets-container"):
                yield Tree("Secrets", id="secrets-tree")

        yield Footer()

    def _get_secret_name(self, node_data: dict) -> str:
        """Construct the full secret name from node data."""
        base_name = node_data["secret_name"]
        version = node_data["version"] if "version" in node_data else "latest"
        return f"{base_name}/versions/{version}"

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle changes in the search input field."""
        if event.input.id == "project-input-search":
            sanitized = sanitize_project_id_search(event.input.value)
            if sanitized != event.input.value:
                event.input.value = sanitized
            self.search_query = sanitized

    def watch_search_query(self, search_query: str) -> None:
        """React to changes in the search query."""
        self._do_search(search_query)

    def watch_current_project(self, project: GCPProject | None) -> None:
        """React to changes in the selected project."""
        if project is not None:
            self._list_secrets()

    @work(thread=True)
    def _do_search(self, search_term: str) -> None:
        """Perform project search and update the tree view."""
        tree = self.query_one("#projects-tree", Tree)
        root = tree.root
        root.expand()
        root.label = "Projects"

        if not search_term:
            return

        try:
            projects = search_gcp_projects(search_term)
            tree.reset("Projects")
            for project in projects:
                leaf_label = f"{project.display_name} ({project.project_id})"
                project_node = tree.root.add_leaf(leaf_label)
                project_node.data = project
        except GoogleAPICallError as e:
            self._notify_gcp_api_error("search projects", e)
        except Exception as e:
            self._notify_general_error("search projects", e)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle project selection in the tree."""
        if event.node.parent == self.query_one("#projects-tree", Tree).root:
            self.current_project = event.node.data

    @work(thread=True)
    def _list_secrets(self) -> None:
        """List secrets for the selected project."""
        tree = self.query_one("#secrets-tree", Tree)
        tree.clear()
        tree.root.label = "Secrets"

        if not self.current_project:
            return

        try:
            secrets = list_secrets(gcp_project=self.current_project)
            for secret in secrets:
                secret_name = secret.name.split("/")[-1]
                secret_node = tree.root.add(secret_name, data={"secret_name": secret.name})

                # Add versions as children
                for version in get_secret_versions(secret):
                    version_number = version.name.split("/")[-1]
                    secret_node.add_leaf(
                        f"Version {version_number} - {version.state.name}",
                        data={
                            "secret_name": secret.name,
                            "version": version_number,
                            "state": version.state.name,
                        },
                    )

                tree.root.expand()
        except GoogleAPICallError as e:
            self._notify_gcp_api_error("load secrets", e)
        except Exception as e:
            self._notify_general_error("load secrets", e)

    def action_secret_preview(self) -> None:
        """Show preview of the selected secret."""
        tree = self.query_one("#secrets-tree", Tree)
        if tree.cursor_node and tree.cursor_node.data:
            secret_name = self._get_secret_name(tree.cursor_node.data)
            self.push_screen(SecretPreview(secret_name))

    def action_edit_secret(self) -> None:
        """Handle the edit secret action."""
        tree = self.query_one("#secrets-tree", Tree)
        if tree.cursor_node and tree.cursor_node.data:
            secret_name = self._get_secret_name(tree.cursor_node.data)
            self._edit_secret(secret_name)

    def _notify_gcp_api_error(self, action: str, error: GoogleAPICallError) -> None:
        """Display formatted API error notification."""
        self.notify(
            f"[b]Failed to {action}: {error.code} {error.reason}[/b]\n"
            f"[d]{format_error_message(str(error.message))}[/d]",
            severity="error",
        )

    def _notify_general_error(self, action: str, error: Exception) -> None:
        """Display formatted general error notification."""
        self.notify(
            f"Failed to {action}: {format_error_message(str(error), 200)}",
            severity="error",
            markup=False,
        )

    def _update_secret(self, secret_name: str, new_content: dict) -> None:
        """Update the secret with new content."""
        try:
            secret_parent = "/".join(secret_name.split("/")[:-2])
            add_secret_version(secret_parent, new_content)
            self.notify("Secret updated successfully", severity="information")
        except GoogleAPICallError as e:
            self._notify_gcp_api_error("update secret", e)
        except Exception as e:
            self._notify_general_error("update secret", e)

    def _edit_secret(self, secret_name: str) -> None:
        """Edit a secret using an external editor."""
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w+") as temp_file:
            try:
                secret_value = get_secret_version_value(secret_name)
            except GoogleAPICallError as e:
                self._notify_gcp_api_error("load secret", e)
                return
            except Exception as e:
                self._notify_general_error("load secret", e)
                return

            json.dump(secret_value, temp_file, indent=2)
            temp_file.flush()
            original_hash = shasum(pathlib.Path(temp_file.name))

            with self.app.suspend():
                os.system(f"{self.EDITOR} {temp_file.name}")

            try:
                new_content = validate_json_content(temp_file)
            except JSONDecodeError as e:
                self.notify(f"JSON decoding error: {str(e)}", severity="error")
                return

            new_hash = shasum(pathlib.Path(temp_file.name))
            if new_hash == original_hash:
                self.notify("No changes detected", severity="information")
                return

            self._update_secret(secret_name, new_content)
            self._list_secrets()


if __name__ == "__main__":
    app = SecretsManager()
    app.run()
