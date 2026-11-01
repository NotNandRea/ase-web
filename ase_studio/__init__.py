# SPDX-FileCopyrightText: 2026 Behnam Farnaghinejad <behnam.farnaghinejad@polito.it>
# SPDX-License-Identifier: GPL-2.0-only
"""ASE Studio frontend and localhost backend."""

from pathlib import Path

__version__ = (Path(__file__).resolve().parent / "VERSION").read_text(
    encoding="utf-8"
).strip()
