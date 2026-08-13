"""
AKI Module Loader
=================

Controlled module discovery and loading layer for AKI.

Responsibilities:
    - Discover explicitly allowed Python modules.
    - Import approved modules.
    - Track loaded modules.
    - Prevent duplicate loading.
    - Provide clear module-loading errors.

IMPORTANT
---------
This module does NOT:

    - execute shell commands
    - execute arbitrary user input
    - provide operating-system access
    - automatically discover arbitrary directories
    - execute plugins without explicit registration

Modules must be explicitly registered or discovered from an
approved package namespace.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from threading import RLock
from types import ModuleType


# ================================================================
# Exceptions
# ================================================================


class ModuleLoaderError(Exception):
    """Base exception for module-loader errors."""


class ModuleRegistrationError(ModuleLoaderError):
    """Raised when a module cannot be registered."""


class ModuleLoadError(ModuleLoaderError):
    """Raised when a registered module cannot be imported."""


# ================================================================
# Module Definition
# ================================================================


@dataclass(frozen=True)
class ModuleDefinition:
    """
    Metadata describing an AKI module.

    Attributes:
        name:
            Internal module identifier.

        import_path:
            Python import path.

        enabled:
            Whether the module is allowed to load.
    """

    name: str
    import_path: str
    enabled: bool = True


# ================================================================
# Module Loader
# ================================================================


class ModuleLoader:
    """
    Controlled loader for AKI Python modules.

    Modules are explicitly registered before loading.
    """

    def __init__(self) -> None:
        self._modules: dict[str, ModuleDefinition] = {}
        self._loaded: dict[str, ModuleType] = {}

        self._lock = RLock()

    # ============================================================
    # Registration
    # ============================================================

    def register(
        self,
        name: str,
        import_path: str,
        *,
        enabled: bool = True,
        replace: bool = False,
    ) -> ModuleDefinition:
        """
        Register an AKI module.

        Example:

            loader.register(
                "telemetry",
                "services.telemetry",
            )
        """

        normalized_name = self._normalize_name(name)
        normalized_path = self._normalize_import_path(
            import_path
        )

        definition = ModuleDefinition(
            name=normalized_name,
            import_path=normalized_path,
            enabled=enabled,
        )

        with self._lock:
            if (
                normalized_name in self._modules
                and not replace
            ):
                raise ModuleRegistrationError(
                    f"Module '{normalized_name}' "
                    "is already registered."
                )

            self._modules[normalized_name] = definition

        return definition

    # ============================================================
    # Unregister
    # ============================================================

    def unregister(
        self,
        name: str,
    ) -> bool:
        """
        Remove a registered module.

        Loaded modules are not automatically unloaded.
        """

        normalized_name = self._normalize_name(name)

        with self._lock:
            if normalized_name not in self._modules:
                return False

            del self._modules[normalized_name]

            return True

    # ============================================================
    # Loading
    # ============================================================

    def load(
        self,
        name: str,
    ) -> ModuleType:
        """
        Load a registered module.

        Returns:
            Imported Python module.

        Raises:
            ModuleLoadError:
                If the module is not registered, disabled,
                or cannot be imported.
        """

        normalized_name = self._normalize_name(name)

        with self._lock:
            definition = self._modules.get(
                normalized_name
            )

            if definition is None:
                raise ModuleLoadError(
                    f"Module '{normalized_name}' "
                    "is not registered."
                )

            if not definition.enabled:
                raise ModuleLoadError(
                    f"Module '{normalized_name}' "
                    "is disabled."
                )

            existing = self._loaded.get(
                normalized_name
            )

            if existing is not None:
                return existing

        try:
            module = importlib.import_module(
                definition.import_path
            )

        except Exception as exc:
            raise ModuleLoadError(
                f"Failed to load module "
                f"'{normalized_name}' "
                f"from '{definition.import_path}'."
            ) from exc

        with self._lock:
            self._loaded[normalized_name] = module

        return module

    # ============================================================
    # Load All
    # ============================================================

    def load_all(self) -> dict[str, ModuleType]:
        """
        Load every enabled registered module.

        Returns:
            Mapping of module name to imported module.

        If one module fails, the error is propagated and loading
        stops at that point.
        """

        with self._lock:
            names = tuple(self._modules.keys())

        loaded: dict[str, ModuleType] = {}

        for name in names:
            module = self.load(name)
            loaded[name] = module

        return loaded

    # ============================================================
    # Reload
    # ============================================================

    def reload(
        self,
        name: str,
    ) -> ModuleType:
        """
        Reload an already loaded module.

        The module must first be registered and loaded.
        """

        normalized_name = self._normalize_name(name)

        with self._lock:
            module = self._loaded.get(
                normalized_name
            )

            if module is None:
                raise ModuleLoadError(
                    f"Module '{normalized_name}' "
                    "has not been loaded."
                )

        try:
            reloaded = importlib.reload(module)

        except Exception as exc:
            raise ModuleLoadError(
                f"Failed to reload module "
                f"'{normalized_name}'."
            ) from exc

        with self._lock:
            self._loaded[normalized_name] = reloaded

        return reloaded

    # ============================================================
    # Query
    # ============================================================

    def get(
        self,
        name: str,
    ) -> ModuleDefinition | None:
        """Return a module definition."""

        normalized_name = self._normalize_name(name)

        with self._lock:
            return self._modules.get(
                normalized_name
            )

    def get_loaded(
        self,
        name: str,
    ) -> ModuleType | None:
        """Return a loaded module."""

        normalized_name = self._normalize_name(name)

        with self._lock:
            return self._loaded.get(
                normalized_name
            )

    def exists(
        self,
        name: str,
    ) -> bool:
        """Return True when a module is registered."""

        normalized_name = self._normalize_name(name)

        with self._lock:
            return normalized_name in self._modules

    def is_loaded(
        self,
        name: str,
    ) -> bool:
        """Return True when a module has been loaded."""

        normalized_name = self._normalize_name(name)

        with self._lock:
            return normalized_name in self._loaded

    # ============================================================
    # Introspection
    # ============================================================

    def registered_modules(
        self,
    ) -> tuple[ModuleDefinition, ...]:
        """Return all registered module definitions."""

        with self._lock:
            return tuple(
                self._modules.values()
            )

    def loaded_modules(
        self,
    ) -> tuple[str, ...]:
        """Return names of currently loaded modules."""

        with self._lock:
            return tuple(
                self._loaded.keys()
            )

    # ============================================================
    # Disable / Enable
    # ============================================================

    def enable(
        self,
        name: str,
    ) -> None:
        """Enable a registered module."""

        normalized_name = self._normalize_name(name)

        with self._lock:
            definition = self._modules.get(
                normalized_name
            )

            if definition is None:
                raise ModuleRegistrationError(
                    f"Unknown module: {normalized_name}"
                )

            self._modules[normalized_name] = (
                ModuleDefinition(
                    name=definition.name,
                    import_path=definition.import_path,
                    enabled=True,
                )
            )

    def disable(
        self,
        name: str,
    ) -> None:
        """Disable a registered module."""

        normalized_name = self._normalize_name(name)

        with self._lock:
            definition = self._modules.get(
                normalized_name
            )

            if definition is None:
                raise ModuleRegistrationError(
                    f"Unknown module: {normalized_name}"
                )

            self._modules[normalized_name] = (
                ModuleDefinition(
                    name=definition.name,
                    import_path=definition.import_path,
                    enabled=False,
                )
            )

    # ============================================================
    # Maintenance
    # ============================================================

    def clear_loaded(self) -> None:
        """
        Forget loaded-module references.

        This does NOT unload Python modules from sys.modules.
        """

        with self._lock:
            self._loaded.clear()

    def clear(self) -> None:
        """Remove all registrations and loaded references."""

        with self._lock:
            self._modules.clear()
            self._loaded.clear()

    # ============================================================
    # Validation
    # ============================================================

    @staticmethod
    def _normalize_name(
        name: str,
    ) -> str:
        """Normalize a module identifier."""

        if not isinstance(name, str):
            raise TypeError(
                "Module name must be a string."
            )

        normalized = name.strip().lower()

        if not normalized:
            raise ValueError(
                "Module name cannot be empty."
            )

        return normalized

    @staticmethod
    def _normalize_import_path(
        import_path: str,
    ) -> str:
        """Validate and normalize a Python import path."""

        if not isinstance(import_path, str):
            raise TypeError(
                "Import path must be a string."
            )

        normalized = import_path.strip()

        if not normalized:
            raise ValueError(
                "Import path cannot be empty."
            )

        if normalized.startswith("."):
            raise ValueError(
                "Relative import paths are not supported."
            )

        if any(
            part == ""
            for part in normalized.split(".")
        ):
            raise ValueError(
                f"Invalid import path: {normalized}"
            )

        return normalized


__all__ = [
    "ModuleDefinition",
    "ModuleLoader",
    "ModuleLoaderError",
    "ModuleLoadError",
    "ModuleRegistrationError",
]