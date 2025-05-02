from google.api_core.exceptions import GoogleAPICallError
from google.cloud import secretmanager
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, Pretty, Static, Tree

from secrets_manager.models.gcp_projects import GCPProject
from secrets_manager.utils.gcp import (
    get_secret_version_value,
    get_secret_versions,
    list_secrets,
    search_gcp_projects,
)
from secrets_manager.utils.helpers import (
    format_error_message,
    sanitize_project_id_search,
    sanitize_secrets,
)


class SecretsManager(App):
    CSS_PATH = "secrets_manager.tcss"
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("p", "secret_preview", "Secret Preview"),
    ]

    search_query = reactive("")
    current_project = reactive(None)

    def __init__(self):
        super().__init__()
        self.client = secretmanager.SecretManagerServiceClient()

    def compose(self) -> ComposeResult:
        """Create child widgets."""
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

    def on_input_changed(self, event: Input.Changed) -> None:
        """Update the search query reactive property."""
        if event.input.id == "project-input-search":
            sanitized = sanitize_project_id_search(event.input.value)
            if sanitized != event.input.value:
                event.input.value = sanitized
            self.search_query = sanitized

    def watch_search_query(self, search_query: str) -> None:
        """React to changes in a search query."""
        self._do_search(search_query)

    def watch_current_project(self, project: "GCPProject") -> None:
        """React to changes in a selected project."""
        if project is not None:
            self._list_secrets()

    @work(thread=True)
    def _do_search(self, search_term: str) -> None:
        """
        Perform project search and update the tree view.
        Running in a separate thread to keep UI responsive.
        """
        tree = self.query_one("#projects-tree", Tree)
        root = tree.root
        root.expand()
        root.label = "Projects"
        try:
            if search_term:
                projects = search_gcp_projects(search_term)
                tree.reset("Projects")
                for project in projects:
                    leaf_label = f"{project.display_name} ({project.project_id})"
                    project_node = tree.root.add_leaf(leaf_label)
                    project_node.data = project
        except GoogleAPICallError as e:
            self.notify(
                f"Failed to search projects: [b]{e.code}[/b]: {format_error_message(str(e.message))}",
                severity="error",
            )
        except Exception as e:
            self.notify(
                f"Failed to search projects: {format_error_message(str(e), 200)}",
                severity="error",
                markup=False,
            )
        return None

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

        if self.current_project:
            try:
                secrets = list_secrets(gcp_project=self.current_project)

                for secret in secrets:
                    secret_name = secret.name.split("/")[-1]

                    # Create a node for each secret
                    secret_node = tree.root.add(secret_name, data={"secret_name": secret.name})

                    # Add versions as children
                    secret_versions = get_secret_versions(secret)
                    for version in secret_versions:
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
                self.notify(
                    f"[b]Failed to load secrets: {e.code} {e.reason}[/b]\n[d]{format_error_message(str(e.message))}[/d]",
                    severity="error",
                )
            except Exception as e:
                self.notify(
                    f"Failed to load secrets: {format_error_message(str(e), 200)}",
                    severity="error",
                    markup=False,
                )

    def action_secret_preview(self):
        tree = self.query_one("#secrets-tree", Tree)
        if tree.cursor_node:
            data = tree.cursor_node.data
            if tree.cursor_node.parent == tree.root:
                # Get latest version if the cursor is on a secret node
                secret_name = f"{data['secret_name']}/versions/latest"
            else:
                # Get specific version if the cursor is on a version node
                secret_name = f"{data['secret_name']}/versions/{data['version']}"
            self.push_screen(SecretPreview(secret_name))


class SecretPreview(ModalScreen):
    def __init__(self, secret_name: str) -> None:
        """Initialize the modal screen with the secret value.

        Args:
            secret_name: The secret value to display
        """
        super().__init__()
        self.secret_name = secret_name

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the modal with a Pretty widget to display the secret."""
        with Vertical(classes="preview-container"):
            # Extract the actual secret name and version from the full path
            parts = self.secret_name.split("/")
            secret_name = parts[-3]
            version = parts[-1]

            yield Static(
                f"Secret: [b]{secret_name}[/b]\nVersion: [b]{version}[/b]", classes="secret-header"
            )
            yield Pretty({}, id="pretty-preview")

    def on_mount(self) -> None:
        self._get_secret(self.secret_name)

    def action_dismiss(self) -> None:
        """Handle the dismiss action to close the modal."""
        self.app.pop_screen()

    @work(thread=True)
    def _get_secret(self, secret_name) -> None:
        secret_value = get_secret_version_value(secret_name)
        sanitized = sanitize_secrets(secret_value)
        self.query_one(Pretty).update(sanitized)


if __name__ == "__main__":
    app = SecretsManager()
    app.run()
