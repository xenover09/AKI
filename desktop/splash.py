"""Animated splash screen for the AKI Desktop Ecosystem.

This module defines :class:`SplashScreen`, a frameless, translucent,
glass-panel widget shown while the application initializes. It displays
the AKI brand, a cycling loading message, an animated progress bar, and
an animated glow effect around the glass panel. All colors are sourced
exclusively from :mod:`desktop.theme.AkiTheme` -- no colors are
hardcoded in this module.

The splash screen contains no business logic. It only manages its own
presentation and a simulated loading sequence intended to be replaced
(or driven) by the real application bootstrap process.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from desktop.themes.aki_theme import AkiTheme


class SplashScreen(QWidget):
    """Frameless animated splash screen for application startup.

    The splash screen renders a centered, translucent glass panel with
    an animated glow border, the AKI title and tagline, a progress bar,
    and a loading label that cycles through a fixed sequence of status
    messages. When the loading sequence completes, :attr:`finished` is
    emitted and the widget fades out and closes itself.

    Attributes:
        finished: Signal emitted once the loading sequence has completed
            and the fade-out animation has finished.
    """

    finished = Signal()

    _LOADING_STEPS: tuple[str, ...] = (
        "Initializing...",
        "Loading Configuration...",
        "Loading Memory...",
        "Loading AI Engine...",
        "Preparing Interface...",
        "Ready...",
    )

    _PANEL_WIDTH: int = 460
    _PANEL_HEIGHT: int = 260
    _STEP_INTERVAL_MS: int = 500
    _FADE_DURATION_MS: int = 400
    _GLOW_MIN_RADIUS: int = 15
    _GLOW_MAX_RADIUS: int = 45

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the splash screen widget.

        Args:
            parent: Optional parent widget. Typically ``None`` since the
                splash screen is a top-level window.
        """
        super().__init__(parent)

        self._current_step: int = 0
        self._progress_value: int = 0

        self._configure_window()
        self._build_ui()
        self._apply_glass_style()
        self._setup_glow_effect()
        self._setup_animations()
        self._center_on_screen()

    def _configure_window(self) -> None:
        """Configure frameless, translucent, always-on-top window flags."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self._PANEL_WIDTH, self._PANEL_HEIGHT)

    def _build_ui(self) -> None:
        """Build and lay out the glass panel and its child widgets."""
        self._glass_panel = QWidget(self)
        self._glass_panel.setObjectName("glassPanel")
        self._glass_panel.setGeometry(0, 0, self._PANEL_WIDTH, self._PANEL_HEIGHT)

        panel_layout = QVBoxLayout(self._glass_panel)
        panel_layout.setContentsMargins(32, 32, 32, 28)
        panel_layout.setSpacing(10)

        self._title_label = QLabel("AKI", self._glass_panel)
        self._title_label.setObjectName("splashTitle")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._subtitle_label = QLabel(
            "Personal AI Operating Ecosystem", self._glass_panel
        )
        self._subtitle_label.setObjectName("splashSubtitle")
        self._subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        panel_layout.addStretch(1)
        panel_layout.addWidget(self._title_label)
        panel_layout.addWidget(self._subtitle_label)
        panel_layout.addStretch(1)

        self._progress_bar = QProgressBar(self._glass_panel)
        self._progress_bar.setObjectName("splashProgressBar")
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(6)
        panel_layout.addWidget(self._progress_bar)

        self._loading_label = QLabel(self._LOADING_STEPS[0], self._glass_panel)
        self._loading_label.setObjectName("splashLoadingLabel")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(self._loading_label)

    def _apply_glass_style(self) -> None:
        """Apply the glass-panel stylesheet using AkiTheme colors only."""
        self._glass_panel.setStyleSheet(
            f"""
            #glassPanel {{
                background-color: {AkiTheme.SURFACE_GLASS};
                border: 1px solid {AkiTheme.BORDER_LIGHT};
                border-radius: 18px;
            }}
            #splashTitle {{
                color: {AkiTheme.TEXT_PRIMARY};
                font-size: 30px;
                font-weight: 700;
                letter-spacing: 4px;
                background: transparent;
                border: none;
            }}
            #splashSubtitle {{
                color: {AkiTheme.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 400;
                background: transparent;
                border: none;
            }}
            #splashLoadingLabel {{
                color: {AkiTheme.TEXT_SECONDARY};
                font-size: 11px;
                background: transparent;
                border: none;
            }}
            #splashProgressBar {{
                background-color: {AkiTheme.SURFACE_CARD};
                border: none;
                border-radius: 3px;
            }}
            #splashProgressBar::chunk {{
                background-color: {AkiTheme.PRIMARY};
                border-radius: 3px;
            }}
            """
        )

    def _setup_glow_effect(self) -> None:
        """Attach an animated drop-shadow glow effect to the glass panel."""
        self._glow_effect = QGraphicsDropShadowEffect(self._glass_panel)
        self._glow_effect.setColor(QColor(AkiTheme.ACCENT))
        self._glow_effect.setOffset(0, 0)
        self._glow_effect.setBlurRadius(self._GLOW_MIN_RADIUS)
        self._glass_panel.setGraphicsEffect(self._glow_effect)

        self._glow_animation = QPropertyAnimation(self._glow_effect, b"blurRadius")
        self._glow_animation.setStartValue(self._GLOW_MIN_RADIUS)
        self._glow_animation.setEndValue(self._GLOW_MAX_RADIUS)
        self._glow_animation.setDuration(1200)
        self._glow_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._glow_animation.setLoopCount(-1)
        self._glow_animation.finished.connect(self._reverse_glow_animation)

    def _reverse_glow_animation(self) -> None:
        """Reverse the glow animation direction to create a pulsing effect."""
        start = self._glow_animation.startValue()
        end = self._glow_animation.endValue()
        self._glow_animation.setStartValue(end)
        self._glow_animation.setEndValue(start)
        self._glow_animation.start()

    def _setup_animations(self) -> None:
        """Prepare the fade-in/fade-out opacity animation and step timer."""
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_in_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_in_animation.setDuration(self._FADE_DURATION_MS)
        self._fade_in_animation.setStartValue(0.0)
        self._fade_in_animation.setEndValue(1.0)
        self._fade_in_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_out_animation = QPropertyAnimation(
            self._opacity_effect, b"opacity"
        )
        self._fade_out_animation.setDuration(self._FADE_DURATION_MS)
        self._fade_out_animation.setStartValue(1.0)
        self._fade_out_animation.setEndValue(0.0)
        self._fade_out_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out_animation.finished.connect(self._on_fade_out_finished)

        self._step_timer = QTimer(self)
        self._step_timer.setInterval(self._STEP_INTERVAL_MS)
        self._step_timer.timeout.connect(self._advance_loading_step)

    def _center_on_screen(self) -> None:
        """Center the splash screen on the primary available screen."""
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        screen_center: QPoint = screen.availableGeometry().center()
        frame = self.frameGeometry()
        frame.moveCenter(screen_center)
        self.move(frame.topLeft())

    def start(self) -> None:
        """Begin the startup animation sequence.

        Fades the splash screen in, starts the glow pulse, and begins
        cycling through the loading steps and progress bar updates.
        """
        self.show()
        self._fade_in_animation.start()
        self._glow_animation.start()
        self._step_timer.start()

    def _advance_loading_step(self) -> None:
        """Advance to the next loading message and update the progress bar."""
        total_steps = len(self._LOADING_STEPS)
        self._current_step += 1

        if self._current_step >= total_steps:
            self._step_timer.stop()
            self._progress_bar.setValue(100)
            self._loading_label.setText(self._LOADING_STEPS[-1])
            QTimer.singleShot(self._STEP_INTERVAL_MS, self._begin_fade_out)
            return

        self._loading_label.setText(self._LOADING_STEPS[self._current_step])
        target_progress = round((self._current_step / (total_steps - 1)) * 100)
        self._animate_progress_to(target_progress)

    def _animate_progress_to(self, target_value: int) -> None:
        """Animate the progress bar smoothly to a target value.

        Args:
            target_value: The progress percentage (0-100) to animate to.
        """
        animation = QPropertyAnimation(self._progress_bar, b"value", self)
        animation.setDuration(self._STEP_INTERVAL_MS)
        animation.setStartValue(self._progress_bar.value())
        animation.setEndValue(target_value)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _begin_fade_out(self) -> None:
        """Stop the glow animation and start the fade-out sequence."""
        self._glow_animation.stop()
        self._fade_out_animation.start()

    def _on_fade_out_finished(self) -> None:
        """Close the splash screen and emit :attr:`finished` after fade-out."""
        self.close()
        self.finished.emit()
