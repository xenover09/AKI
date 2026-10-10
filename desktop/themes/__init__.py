"""Theme package for the AKI desktop application.

Exposes the concrete theme implementations available to the desktop
shell. Currently only :class:`~desktop.themes.aki_theme.AkiTheme` is
provided, but the package boundary exists so that additional themes
(dark neon, light, high-contrast, etc.) can be added later without
touching consumers that import from ``desktop.themes``.
"""

from __future__ import annotations

from desktop.themes.aki_theme import AkiTheme

__all__ = ["AkiTheme"]
