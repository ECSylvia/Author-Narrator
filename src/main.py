import sys
import os
from pathlib import Path

# Preserve direct-script, module and existing console entry points.
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.integrations.doxie_hub import (
    HubIntegrationError, ProjectBindings, prepare_launch,
)


def main():
    try:
        launch = prepare_launch(sys.argv[1:])
    except HubIntegrationError as exc:
        print(f"Doxie Hub: {exc}", file=sys.stderr)
        return 2

    # Reject unsafe Hub configuration before creating UI or loading providers.
    from PySide6.QtWidgets import QApplication
    app = QApplication([sys.argv[0], *launch.qt_arguments])
    if launch.session is None:
        from src.ui.main_window import MainWindow
        window = MainWindow()
    else:
        from src.ui.hub_window import HubMainWindow
        bindings = ProjectBindings(Path.home() / ".author_narrator_hub" / "dev-links.json")
        window = HubMainWindow(launch.session, bindings, launch.local_project)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
