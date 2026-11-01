#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Behnam Farnaghinejad <behnam.farnaghinejad@polito.it>
# SPDX-License-Identifier: GPL-2.0-only
"""Show the Linux desktop's application chooser for one assembly source."""
from __future__ import annotations

import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gio, Gtk  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        return 2
    source_path = Path(sys.argv[1]).resolve()
    if not source_path.is_file():
        return 2

    source = Gio.File.new_for_path(str(source_path))
    dialog = Gtk.AppChooserDialog.new(None, Gtk.DialogFlags.MODAL, source)
    dialog.set_title("Open with")
    dialog.set_heading(f"Open {source_path.name} with")
    dialog.set_default_size(620, 460)
    chooser = dialog.get_widget()
    if chooser is not None:
        chooser.set_show_all(True)

    response = dialog.run()
    application = dialog.get_app_info() if response == Gtk.ResponseType.OK else None
    dialog.destroy()
    if application is not None:
        application.launch([source], None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
