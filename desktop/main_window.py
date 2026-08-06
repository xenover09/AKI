"""Primary application window for the AKI desktop operating system.

This module defines :class:`MainWindow`, the root shell of the AKI
(Artificial Knowledge Intelligence) desktop application. The window is
responsible for composing the frameless glass chrome, wiring the
:class:`~desktop.sidebar.Sidebar`, :class:`~desktop.title_bar.TitleBar`,
:class:`~desktop.navigation.NavigationController` and
:class:`~desktop.page_manager.PageManager` together, registering every
first-party page, and exposing the extension points that later subsystems
(command palette, notification center, AI brain, plugin loading) attach
to.

Typical usage example:

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
"""

from __future__ import annotations

import importlib.util
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Callable, Dict, List, Optional, Protocol, runtime_checkable

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from desktop.navigation import NavigationController
from desktop.page_manager import PageManager
from desktop.sidebar import Sidebar
from desktop.title_bar import TitleBar
from desktop.themes.blue_theme import BlueTheme

from desktop.pages.automation_page import AutomationPage
from desktop.pages.chat_page import ChatPage
from desktop.pages.cyber_page import CyberPage
from desktop.pages.dashboard_page import DashboardPage
from desktop.pages.developer_page import DeveloperPage
from desktop.pages.memory_page import MemoryPage
from desktop.pages.plugins_page import PluginsPage
from desktop.pages.settings_page import SettingsPage
from desktop.pages.vision_page import VisionPage
from desktop.pages.voice_page import VoicePage

logger = logging.getLogger(__name__)


class Route:
    """Canonical route identifiers used across navigation and paging.

    These string constants are the single source of truth for route
    identifiers so that the sidebar, navigation controller and page
    manager never rely on magic strings scattered across the codebase.
    """

    DASHBOARD: str = "dashboard"
    CHAT: str = "chat"
    VOICE: str = "voice"
    VISION: str = "vision"
    MEMORY: str = "memory"
    AUTOMATION: str = "automation"
    CYBER: str = "cyber"
    DEVELOPER: str = "developer"
    PLUGINS: str = "plugins"
    SETTINGS: str = "settings"


class AppEventBus(QObject):
    """Application-wide publish/subscribe event bus.

    Central subsystems (command palette, notification center, AI brain,
    plugins) communicate through this bus instead of holding direct
    references to :class:`MainWindow`, keeping the window decoupled from
    its extensions.

    Attributes:
        notification_posted: Emitted with ``(title, message)`` whenever a
            subsystem wants to surface a toast notification.
        command_invoked: Emitted with the identifier of a command that was
            selected in the command palette.
        route_changed: Emitted with the new route identifier whenever
            navigation completes.
    """

    notification_posted: Signal = Signal(str, str)
    command_invoked: Signal = Signal(str)
    route_changed: Signal = Signal(str)


@dataclass(frozen=True)
class Command:
    """A single entry exposed through the command palette.

    Attributes:
        identifier: Unique, stable identifier for the command.
        title: Human readable label shown in the palette list.
        handler: Zero-argument callable executed when the command runs.
    """

    identifier: str
    title: str
    handler: Callable[[], None]


class CommandPaletteOverlay(QWidget):
    """Filterable overlay used to search and execute registered commands.

    The overlay is created hidden and is raised above the page stack on
    demand. It is intentionally lightweight today so that a future
    natural-language command router can be layered on top of it without
    changing its public surface.
    """

    def __init__(self, parent: QWidget) -> None:
        """Initialize the overlay.

        Args:
            parent: Widget the overlay is stacked on top of.
        """
        super().__init__(parent)
        self.setObjectName("commandPaletteOverlay")
        self.setVisible(False)
        self._commands: Dict[str, Command] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)

        self._search_field = QLineEdit(self)
        self._search_field.setObjectName("commandPaletteSearch")
        self._search_field.setPlaceholderText("Type a command…")
        self._search_field.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self._search_field)

        self._results_list = QListWidget(self)
        self._results_list.setObjectName("commandPaletteResults")
        self._results_list.itemActivated.connect(self._on_item_activated)
        layout.addWidget(self._results_list)

    def register_command(self, command: Command) -> None:
        """Register or replace a command exposed by the palette.

        Args:
            command: Command definition to register.
        """
        self._commands[command.identifier] = command
        self._refresh_results(self._search_field.text())

    def show_overlay(self) -> None:
        """Show the overlay, resize it to the parent and focus the search box."""
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(QRect(0, 0, parent.width(), parent.height()))
        self._search_field.clear()
        self._refresh_results("")
        self.raise_()
        self.setVisible(True)
        self._search_field.setFocus(Qt.FocusReason.PopupFocusReason)

    def hide_overlay(self) -> None:
        """Hide the overlay."""
        self.setVisible(False)

    def _on_filter_changed(self, text: str) -> None:
        """Refresh the results list when the search text changes.

        Args:
            text: Current contents of the search field.
        """
        self._refresh_results(text)

    def _refresh_results(self, query: str) -> None:
        """Rebuild the visible results for the given query.

        Args:
            query: Case-insensitive substring to filter command titles by.
        """
        self._results_list.clear()
        normalized_query = query.strip().lower()
        for command in self._commands.values():
            if normalized_query in command.title.lower():
                item = QListWidgetItem(command.title)
                item.setData(Qt.ItemDataRole.UserRole, command.identifier)
                self._results_list.addItem(item)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        """Execute the command backing the activated list item.

        Args:
            item: The list item the user activated.
        """
        identifier = item.data(Qt.ItemDataRole.UserRole)
        command = self._commands.get(identifier)
        self.hide_overlay()
        if command is not None:
            command.handler()

    def keyPressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Close the overlay when Escape is pressed.

        Args:
            event: The key event to inspect.
        """
        if event.key() == Qt.Key.Key_Escape:
            self.hide_overlay()
            return
        super().keyPressEvent(event)


class NotificationCenter(QWidget):
    """Toast-style notification stack anchored to the top-right corner."""

    _MAX_VISIBLE: int = 5
    _TOAST_LIFETIME_MS: int = 5000

    def __init__(self, parent: QWidget) -> None:
        """Initialize the notification center.

        Args:
            parent: Widget the notification stack is layered on top of.
        """
        super().__init__(parent)
        self.setObjectName("notificationCenter")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self._layout.addStretch(1)
        self.setVisible(True)

    def post(self, title: str, message: str) -> None:
        """Display a new toast notification.

        Args:
            title: Bold headline of the notification.
            message: Supporting body text of the notification.
        """
        toast = self._build_toast(title, message)
        self._layout.insertWidget(self._layout.count() - 1, toast)
        self._enforce_max_visible()
        self._reposition()
        from PySide6.QtCore import QTimer

        QTimer.singleShot(self._TOAST_LIFETIME_MS, lambda: self._remove_toast(toast))

    def _build_toast(self, title: str, message: str) -> QWidget:
        """Construct a single toast widget.

        Args:
            title: Bold headline of the notification.
            message: Supporting body text of the notification.

        Returns:
            The constructed toast widget, not yet inserted into the layout.
        """
        toast = QWidget(self)
        toast.setObjectName("toastNotification")
        toast_layout = QVBoxLayout(toast)
        toast_layout.setContentsMargins(12, 8, 12, 8)
        title_label = QLabel(title, toast)
        title_label.setObjectName("toastTitle")
        message_label = QLabel(message, toast)
        message_label.setObjectName("toastMessage")
        message_label.setWordWrap(True)
        toast_layout.addWidget(title_label)
        toast_layout.addWidget(message_label)
        toast.setFixedWidth(300)
        return toast

    def _remove_toast(self, toast: QWidget) -> None:
        """Remove a toast from the layout and dispose of it.

        Args:
            toast: The toast widget to remove.
        """
        self._layout.removeWidget(toast)
        toast.deleteLater()
        self._reposition()

    def _enforce_max_visible(self) -> None:
        """Drop the oldest toasts beyond the configured maximum."""
        toast_count = self._layout.count() - 1
        while toast_count > self._MAX_VISIBLE:
            oldest = self._layout.itemAt(0).widget()
            if oldest is not None:
                self._remove_toast(oldest)
            toast_count -= 1

    def _reposition(self) -> None:
        """Anchor the notification stack to the top-right of the parent."""
        parent = self.parentWidget()
        if parent is None:
            return
        width = 320
        self.setGeometry(QRect(parent.width() - width - 16, 16, width, parent.height() - 32))


class AIBrainInterface(ABC):
    """Contract every AI brain implementation must satisfy.

    A concrete brain is responsible for turning free-form user queries
    into responses, routing to tools, and orchestrating memory, voice and
    vision subsystems. :class:`MainWindow` only depends on this
    interface, never on a concrete implementation.
    """

    @abstractmethod
    def process_query(self, query: str) -> str:
        """Process a natural-language query and return a textual response.

        Args:
            query: The raw text submitted by the user.

        Returns:
            The textual response produced by the brain.
        """
        ...

    @abstractmethod
    def shutdown(self) -> None:
        """Release any resources held by the brain implementation."""
        ...


class NullAIBrain(AIBrainInterface):
    """Fail-fast default brain used until a real brain is attached.

    Keeping a concrete null object (instead of leaving the reference as
    ``None``) lets :class:`MainWindow` always call through
    ``self._ai_brain`` without null checks scattered across the class.
    """

    def process_query(self, query: str) -> str:
        """Raise because no brain implementation has been attached yet.

        Args:
            query: The raw text submitted by the user.

        Returns:
            Never returns.

        Raises:
            RuntimeError: Always, until :meth:`MainWindow.attach_ai_brain`
                is called with a real implementation.
        """
        raise RuntimeError(
            "No AI brain is attached to AKI yet. Call "
            "MainWindow.attach_ai_brain() with a concrete "
            "AIBrainInterface implementation before issuing queries."
        )

    def shutdown(self) -> None:
        """No-op shutdown, since no resources are held."""
        logger.debug("NullAIBrain.shutdown() called; nothing to release.")


@runtime_checkable
class PluginModule(Protocol):
    """Structural contract expected from a plugin's entry-point module."""

    def register(self, context: "PluginContext") -> None:
        """Register the plugin's capabilities with the host application.

        Args:
            context: The context object exposing safe integration points.
        """
        ...


@dataclass
class PluginContext:
    """Integration surface handed to every plugin on registration.

    Attributes:
        main_window: The owning :class:`MainWindow` instance.
        event_bus: The application-wide event bus.
        register_page: Callable used to register a new page and route.
        register_command: Callable used to register a command palette entry.
    """

    main_window: "MainWindow"
    event_bus: AppEventBus
    register_page: Callable[[str, QWidget, str], None]
    register_command: Callable[[Command], None]


class PluginLoader:
    """Discovers and loads AKI plugins from a directory on disk."""

    def __init__(self, plugins_directory: Path) -> None:
        """Initialize the loader.

        Args:
            plugins_directory: Directory scanned for ``*.py`` plugin
                modules. It is created if it does not already exist.
        """
        self._plugins_directory = plugins_directory
        self._plugins_directory.mkdir(parents=True, exist_ok=True)
        self._loaded_modules: Dict[str, ModuleType] = {}

    def load_all(self, context: PluginContext) -> List[str]:
        """Load every plugin module found in the plugins directory.

        Args:
            context: Context object passed to each plugin's ``register``
                function.

        Returns:
            The list of plugin module names that were loaded successfully.
        """
        loaded: List[str] = []
        for module_path in sorted(self._plugins_directory.glob("*.py")):
            module_name = f"aki_plugin_{module_path.stem}"
            try:
                module = self._import_module(module_name, module_path)
                if isinstance(module, PluginModule):
                    module.register(context)
                    self._loaded_modules[module_name] = module
                    loaded.append(module_name)
                else:
                    logger.warning(
                        "Plugin '%s' does not expose a register(context) "
                        "function and was skipped.",
                        module_path.name,
                    )
            except Exception:
                logger.exception(
                    "Failed to load plugin '%s'; continuing with remaining "
                    "plugins.",
                    module_path.name,
                )
        return loaded

    def _import_module(self, module_name: str, module_path: Path) -> ModuleType:
        """Import a single plugin module from a file path.

        Args:
            module_name: Synthetic module name to register in ``sys.modules``.
            module_path: Filesystem path of the plugin's source file.

        Returns:
            The imported module object.

        Raises:
            ImportError: If the module could not be loaded from the given
                path.
        """
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot create import spec for '{module_path}'.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


class MainWindow(QMainWindow):
    """Root window of the AKI desktop operating system.

    The window renders a frameless, glass-styled chrome composed of a
    custom :class:`TitleBar`, a :class:`Sidebar`, and a page stack driven
    by :class:`PageManager`. All navigation flows through a single
    :class:`NavigationController` instance so that sidebar clicks, command
    palette invocations and programmatic navigation share one code path.
    """

    _RESIZE_MARGIN: int = 6
    _CORNER_RADIUS: float = 14.0

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Construct and wire up the main window.

        Args:
            parent: Optional parent widget, normally ``None`` for a
                top-level window.
        """
        super().__init__(parent)

        self._theme = BlueTheme()
        self._event_bus = AppEventBus(self)
        self._navigation_controller = NavigationController(self)
        self._page_manager: Optional[PageManager] = None
        self._stacked_widget = QStackedWidget(self)
        self._ai_brain: AIBrainInterface = NullAIBrain()
        self._plugin_loader = PluginLoader(Path.cwd() / "plugins")

        self._drag_offset: Optional[QPoint] = None
        self._resize_edges: Qt.Edges = Qt.Edges()
        self._resizing: bool = False
        self._normal_geometry: QRect = QRect()

        self._configure_window_flags()
        self._build_chrome()
        self._register_pages()
        self._wire_navigation()
        self._wire_title_bar()
        self._wire_sidebar()
        self._register_default_commands()
        self._apply_theme()

        self._navigation_controller.navigate(Route.DASHBOARD)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    def _configure_window_flags(self) -> None:
        """Configure the frameless, translucent glass window flags."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setMinimumSize(1024, 640)
        self.resize(1440, 900)
        self.setWindowTitle("AKI — Artificial Knowledge Intelligence")

    def _build_chrome(self) -> None:
        """Assemble the title bar, sidebar and page stack into the window."""
        central_widget = QWidget(self)
        central_widget.setObjectName("mainWindowCentralWidget")
        central_widget.setMouseTracking(True)

        shadow = QGraphicsDropShadowEffect(central_widget)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 160))
        central_widget.setGraphicsEffect(shadow)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(1, 1, 1, 1)
        root_layout.setSpacing(0)

        self._title_bar = TitleBar(central_widget)
        self._title_bar.setObjectName("mainWindowTitleBar")
        self._title_bar.installEventFilter(self)
        root_layout.addWidget(self._title_bar)

        body_widget = QWidget(central_widget)
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self._sidebar = Sidebar(body_widget)
        self._sidebar.setObjectName("mainWindowSidebar")
        body_layout.addWidget(self._sidebar)

        self._stacked_widget.setObjectName("mainWindowStack")
        self._page_manager = PageManager(self._stacked_widget)
        body_layout.addWidget(self._stacked_widget, 1)

        root_layout.addWidget(body_widget, 1)
        self.setCentralWidget(central_widget)

        self._command_palette = CommandPaletteOverlay(central_widget)
        self._notification_center = NotificationCenter(central_widget)
        self._notification_center._reposition()

    def _register_pages(self) -> None:
        """Instantiate every first-party page and register it with the
        page manager and navigation controller."""
        assert self._page_manager is not None
        page_registry: Dict[str, QWidget] = {
            Route.DASHBOARD: DashboardPage(self),
            Route.CHAT: ChatPage(self),
            Route.VOICE: VoicePage(self),
            Route.VISION: VisionPage(self),
            Route.MEMORY: MemoryPage(self),
            Route.AUTOMATION: AutomationPage(self),
            Route.CYBER: CyberPage(self),
            Route.DEVELOPER: DeveloperPage(self),
            Route.PLUGINS: PluginsPage(self),
            Route.SETTINGS: SettingsPage(self),
        }
        for route_id, page_widget in page_registry.items():
            self._page_manager.register_page(route_id, page_widget)
            self._navigation_controller.register_route(route_id)

    def _wire_navigation(self) -> None:
        """Connect the navigation controller to the page manager and bus."""
        assert self._page_manager is not None
        self._navigation_controller.navigation_changed.connect(
            self._page_manager.show_page
        )
        self._navigation_controller.navigation_changed.connect(
            self._sidebar.set_active
        )
        self._navigation_controller.navigation_changed.connect(
            self._event_bus.route_changed.emit
        )

    def _wire_title_bar(self) -> None:
        """Connect title bar window-control signals to their handlers."""
        self._title_bar.minimize_requested.connect(self._handle_minimize)
        self._title_bar.maximize_requested.connect(self._handle_maximize_restore)
        self._title_bar.close_requested.connect(self._handle_close)

    def _wire_sidebar(self) -> None:
        """Connect sidebar navigation requests to the navigation controller."""
        self._sidebar.navigation_requested.connect(
            self._navigation_controller.navigate
        )

    def _register_default_commands(self) -> None:
        """Register the built-in command palette entries."""
        route_titles: Dict[str, str] = {
            Route.DASHBOARD: "Go to Dashboard",
            Route.CHAT: "Go to Chat",
            Route.VOICE: "Go to Voice",
            Route.VISION: "Go to Vision",
            Route.MEMORY: "Go to Memory",
            Route.AUTOMATION: "Go to Automation",
            Route.CYBER: "Go to Cyber",
            Route.DEVELOPER: "Go to Developer",
            Route.PLUGINS: "Go to Plugins",
            Route.SETTINGS: "Go to Settings",
        }
        for route_id, title in route_titles.items():
            self._command_palette.register_command(
                Command(
                    identifier=f"navigate.{route_id}",
                    title=title,
                    handler=lambda checked=False, r=route_id: self._navigation_controller.navigate(r),
                )
            )
        self._command_palette.register_command(
            Command(
                identifier="window.toggle_maximize",
                title="Toggle Maximize Window",
                handler=self._handle_maximize_restore,
            )
        )

    def _apply_theme(self) -> None:
        """Apply the blue glass theme stylesheet to the window."""
        self.setStyleSheet(self._theme.stylesheet())

    # ------------------------------------------------------------------
    # Public extension points
    # ------------------------------------------------------------------

    def attach_ai_brain(self, brain: AIBrainInterface) -> None:
        """Attach a concrete AI brain implementation.

        Args:
            brain: The brain implementation to activate. Replaces and
                shuts down any previously attached brain.
        """
        self._ai_brain.shutdown()
        self._ai_brain = brain
        self._notification_center.post("AI Brain", "AKI brain connected.")

    def submit_query_to_brain(self, query: str) -> str:
        """Forward a natural-language query to the attached AI brain.

        Args:
            query: The raw text submitted by the user.

        Returns:
            The textual response produced by the brain.
        """
        return self._ai_brain.process_query(query)

    def load_plugins(self) -> List[str]:
        """Discover and load every plugin from the plugins directory.

        Returns:
            The list of plugin module names that loaded successfully.
        """
        assert self._page_manager is not None
        context = PluginContext(
            main_window=self,
            event_bus=self._event_bus,
            register_page=self._register_plugin_page,
            register_command=self._command_palette.register_command,
        )
        loaded = self._plugin_loader.load_all(context)
        if loaded:
            self._notification_center.post(
                "Plugins Loaded", f"{len(loaded)} plugin(s) loaded successfully."
            )
        return loaded

    def _register_plugin_page(self, route_id: str, page: QWidget, sidebar_label: str) -> None:
        """Register a page contributed by a plugin.

        Args:
            route_id: Unique route identifier for the new page.
            page: The page widget to register.
            sidebar_label: Label shown for the route in the sidebar.
        """
        assert self._page_manager is not None
        self._page_manager.register_page(route_id, page)
        self._navigation_controller.register_route(route_id)
        self._sidebar.add_dynamic_entry(route_id, sidebar_label)

    def show_command_palette(self) -> None:
        """Show the command palette overlay."""
        self._command_palette.show_overlay()

    def hide_command_palette(self) -> None:
        """Hide the command palette overlay."""
        self._command_palette.hide_overlay()

    def post_notification(self, title: str, message: str) -> None:
        """Post a toast notification to the notification center.

        Args:
            title: Bold headline of the notification.
            message: Supporting body text of the notification.
        """
        self._notification_center.post(title, message)

    @property
    def event_bus(self) -> AppEventBus:
        """AppEventBus: The application-wide event bus."""
        return self._event_bus

    @property
    def navigation_controller(self) -> NavigationController:
        """NavigationController: The window's navigation controller."""
        return self._navigation_controller

    # ------------------------------------------------------------------
    # Window control slots
    # ------------------------------------------------------------------

    def _handle_minimize(self) -> None:
        """Minimize the window."""
        self.showMinimized()

    def _handle_maximize_restore(self) -> None:
        """Toggle between maximized and restored window states."""
        if self.isMaximized():
            self.showNormal()
            self._title_bar.set_maximized(False)
        else:
            self._normal_geometry = self.geometry()
            self.showMaximized()
            self._title_bar.set_maximized(True)

    def _handle_close(self) -> None:
        """Close the window, releasing brain resources first."""
        self._ai_brain.shutdown()
        self.close()

    # ------------------------------------------------------------------
    # Frameless drag / resize handling
    # ------------------------------------------------------------------

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        """Handle title bar drag-to-move and double-click-to-maximize.

        Args:
            watched: The object the event originated from.
            event: The event to process.

        Returns:
            ``True`` if the event was consumed, ``False`` to let it
            propagate normally.
        """
        if watched is self._title_bar:
            if event.type() == QEvent.Type.MouseButtonPress:
                mouse_event = event  # type: ignore[assignment]
                if isinstance(mouse_event, QMouseEvent) and mouse_event.button() == Qt.MouseButton.LeftButton:
                    self._drag_offset = mouse_event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    return False
            elif event.type() == QEvent.Type.MouseMove:
                mouse_event = event  # type: ignore[assignment]
                if (
                    isinstance(mouse_event, QMouseEvent)
                    and self._drag_offset is not None
                    and mouse_event.buttons() & Qt.MouseButton.LeftButton
                    and not self.isMaximized()
                ):
                    self.move(mouse_event.globalPosition().toPoint() - self._drag_offset)
                    return False
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_offset = None
            elif event.type() == QEvent.Type.MouseButtonDblClick:
                self._handle_maximize_restore()
                return True
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Begin an edge-resize gesture when pressing near a window border.

        Args:
            event: The mouse press event.
        """
        if event.button() == Qt.MouseButton.LeftButton and not self.isMaximized():
            self._resize_edges = self._edges_at(event.position().toPoint())
            self._resizing = self._resize_edges != Qt.Edges()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """Perform an in-progress resize or update the resize cursor.

        Args:
            event: The mouse move event.
        """
        if self._resizing and event.buttons() & Qt.MouseButton.LeftButton:
            self._perform_resize(event.globalPosition().toPoint())
        elif not self.isMaximized():
            edges = self._edges_at(event.position().toPoint())
            self._update_cursor_for_edges(edges)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        """End an in-progress resize gesture.

        Args:
            event: The mouse release event.
        """
        self._resizing = False
        self._resize_edges = Qt.Edges()
        self.unsetCursor()
        super().mouseReleaseEvent(event)

    def _edges_at(self, position: QPoint) -> Qt.Edges:
        """Determine which window edges a point lies within resize range of.

        Args:
            position: Point in local window coordinates.

        Returns:
            The combination of :class:`Qt.Edge` flags the point is near.
        """
        margin = self._RESIZE_MARGIN
        edges = Qt.Edges()
        if position.x() <= margin:
            edges |= Qt.Edge.LeftEdge
        if position.x() >= self.width() - margin:
            edges |= Qt.Edge.RightEdge
        if position.y() <= margin:
            edges |= Qt.Edge.TopEdge
        if position.y() >= self.height() - margin:
            edges |= Qt.Edge.BottomEdge
        return edges

    def _update_cursor_for_edges(self, edges: Qt.Edges) -> None:
        """Set the mouse cursor shape appropriate for the given edges.

        Args:
            edges: The combination of edges the cursor currently hovers.
        """
        if (edges & Qt.Edge.LeftEdge and edges & Qt.Edge.TopEdge) or (
            edges & Qt.Edge.RightEdge and edges & Qt.Edge.BottomEdge
        ):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif (edges & Qt.Edge.RightEdge and edges & Qt.Edge.TopEdge) or (
            edges & Qt.Edge.LeftEdge and edges & Qt.Edge.BottomEdge
        ):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif edges & Qt.Edge.LeftEdge or edges & Qt.Edge.RightEdge:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edges & Qt.Edge.TopEdge or edges & Qt.Edge.BottomEdge:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.unsetCursor()

    def _perform_resize(self, global_position: QPoint) -> None:
        """Resize the window based on the active edges and pointer position.

        Args:
            global_position: Current global-space pointer position.
        """
        geometry = self.geometry()
        new_geometry = QRect(geometry)

        if self._resize_edges & Qt.Edge.LeftEdge:
            new_geometry.setLeft(global_position.x())
        if self._resize_edges & Qt.Edge.RightEdge:
            new_geometry.setRight(global_position.x())
        if self._resize_edges & Qt.Edge.TopEdge:
            new_geometry.setTop(global_position.y())
        if self._resize_edges & Qt.Edge.BottomEdge:
            new_geometry.setBottom(global_position.y())

        minimum = self.minimumSize()
        if new_geometry.width() < minimum.width():
            if self._resize_edges & Qt.Edge.LeftEdge:
                new_geometry.setLeft(new_geometry.right() - minimum.width())
            else:
                new_geometry.setRight(new_geometry.left() + minimum.width())
        if new_geometry.height() < minimum.height():
            if self._resize_edges & Qt.Edge.TopEdge:
                new_geometry.setTop(new_geometry.bottom() - minimum.height())
            else:
                new_geometry.setBottom(new_geometry.top() + minimum.height())

        self.setGeometry(new_geometry)

    # ------------------------------------------------------------------
    # Painting and layout events
    # ------------------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:  # type: ignore[override]
        """Paint the rounded glass background of the window.

        Args:
            event: The paint event.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        path = QPainterPath()
        radius = 0.0 if self.isMaximized() else self._CORNER_RADIUS
        path.addRoundedRect(self.rect(), radius, radius)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(18, 22, 34, 235))
        painter.drawPath(path)

        border_color = QColor(90, 140, 255, 90)
        painter.setPen(border_color)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        painter.end()
        super().paintEvent(event)

    def resizeEvent(self, event: QEvent) -> None:  # type: ignore[override]
        """Reposition floating overlays whenever the window is resized.

        Args:
            event: The resize event.
        """
        super().resizeEvent(event)
        if hasattr(self, "_notification_center"):
            self._notification_center._reposition()
        if hasattr(self, "_command_palette") and self._command_palette.isVisible():
            self._command_palette.setGeometry(QRect(0, 0, self.width(), self.height()))

    def changeEvent(self, event: QEvent) -> None:  # type: ignore[override]
        """Keep the title bar's maximize icon in sync with window state.

        Args:
            event: The change event.
        """
        if event.type() == QEvent.Type.WindowStateChange:
            self._title_bar.set_maximized(self.isMaximized())
        super().changeEvent(event)


def run_aki_application(argv: List[str]) -> int:
    """Bootstrap and execute the AKI desktop application.

    Args:
        argv: Command line arguments, typically ``sys.argv``.

    Returns:
        The process exit code returned by the Qt event loop.
    """
    application = QApplication(argv)
    window = MainWindow()
    window.load_plugins()
    window.show()
    return application.exec()
