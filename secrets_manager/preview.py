from google.api_core.exceptions import GoogleAPICallError
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Pretty, Static

from secrets_manager.utils.gcp import (
    get_secret_version_value,
)
from secrets_manager.utils.helpers import (
    format_error_message,
    sanitize_secrets,
)


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
        try:
            secret_value = get_secret_version_value(secret_name)
            secret_to_preview = sanitize_secrets(secret_value)
            self.query_one(Pretty).update(secret_to_preview)
        except GoogleAPICallError as e:
            self.notify(
                f"[b]Failed to preview secret: {e.code} {e.reason}[/b]\n[d]{format_error_message(str(e.message))}[/d]",
                severity="error",
                markup=False,
            )
            self.action_dismiss()
        except Exception as e:
            self.notify(
                f"Failed to preview secret: {format_error_message(str(e), 200)}",
                severity="error",
                markup=False,
            )
            self.action_dismiss()
