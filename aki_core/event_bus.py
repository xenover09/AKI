"""
AKI Event Bus
=============

Central event communication layer for AKI.

The EventBus allows independent AKI modules to communicate without
creating tight dependencies between them.

Example:

    CommandRouter
        ↓
    EventBus
        ↓
    UI / Logger / Memory / Services

IMPORTANT
---------
This module does NOT execute operating-system actions.

It only transports events between application components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable
from uuid import uuid4


# ================================================================
# Event
# ================================================================


@dataclass(frozen=True)
class AKIEvent:
    """
    Immutable event published through the AKI EventBus.

    Attributes:
        name:
            Event name, for example ``command.received``.

        data:
            Event payload.

        event_id:
            Unique identifier for this event.

        timestamp:
            UTC timestamp when the event was created.

        source:
            Component that generated the event.
    """

    name: str
    data: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    source: str = "unknown"


# ================================================================
# Handler Type
# ================================================================


EventHandler = Callable[[AKIEvent], None]


# ================================================================
# Event Bus
# ================================================================


class EventBus:
    """
    Thread-safe publish/subscribe event bus.

    Components can:

        subscribe()
        unsubscribe()
        publish()

    No component needs to know the internal implementation of
    another component.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._lock = RLock()

    # ------------------------------------------------------------
    # Subscribe
    # ------------------------------------------------------------

    def subscribe(
        self,
        event_name: str,
        handler: EventHandler,
    ) -> None:
        """
        Subscribe a handler to an event.

        Example:

            bus.subscribe(
                "command.received",
                handle_command,
            )
        """

        name = self._normalize_event_name(event_name)

        if not callable(handler):
            raise TypeError(
                "handler must be callable."
            )

        with self._lock:
            handlers = self._handlers.setdefault(name, [])

            if handler not in handlers:
                handlers.append(handler)

    # ------------------------------------------------------------
    # Unsubscribe
    # ------------------------------------------------------------

    def unsubscribe(
        self,
        event_name: str,
        handler: EventHandler,
    ) -> bool:
        """
        Remove a handler from an event.

        Returns:
            True if the handler was removed.
            False if it was not registered.
        """

        name = self._normalize_event_name(event_name)

        with self._lock:
            handlers = self._handlers.get(name)

            if not handlers:
                return False

            try:
                handlers.remove(handler)
            except ValueError:
                return False

            if not handlers:
                self._handlers.pop(name, None)

            return True

    # ------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------

    def publish(
        self,
        event: AKIEvent,
    ) -> None:
        """
        Publish an event to all subscribed handlers.

        Handler execution occurs outside the internal lock so one
        slow handler does not block subscription changes.
        """

        if not isinstance(event, AKIEvent):
            raise TypeError(
                "event must be an AKIEvent instance."
            )

        with self._lock:
            handlers = tuple(
                self._handlers.get(event.name, ())
            )

        for handler in handlers:
            try:
                handler(event)

            except Exception:
                # Event handlers must not break the event bus itself.
                #
                # Logging will be connected later through AKI's
                # logging/diagnostics layer.
                continue

    # ------------------------------------------------------------
    # Convenience Publish
    # ------------------------------------------------------------

    def emit(
        self,
        event_name: str,
        *,
        data: dict[str, Any] | None = None,
        source: str = "unknown",
    ) -> AKIEvent:
        """
        Create and publish an event.

        Returns:
            The created AKIEvent.
        """

        event = AKIEvent(
            name=self._normalize_event_name(event_name),
            data=dict(data or {}),
            source=source,
        )

        self.publish(event)

        return event

    # ------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------

    def has_subscribers(
        self,
        event_name: str,
    ) -> bool:
        """Return True if an event has registered handlers."""

        name = self._normalize_event_name(event_name)

        with self._lock:
            return bool(self._handlers.get(name))

    def subscriber_count(
        self,
        event_name: str,
    ) -> int:
        """Return the number of handlers subscribed to an event."""

        name = self._normalize_event_name(event_name)

        with self._lock:
            return len(
                self._handlers.get(name, ())
            )

    def subscribed_events(self) -> tuple[str, ...]:
        """Return all events that currently have subscribers."""

        with self._lock:
            return tuple(self._handlers.keys())

    # ------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------

    def clear(
        self,
        event_name: str | None = None,
    ) -> None:
        """
        Remove subscriptions.

        If event_name is provided, only that event is cleared.

        If omitted, every subscription is removed.
        """

        with self._lock:
            if event_name is None:
                self._handlers.clear()
                return

            name = self._normalize_event_name(event_name)
            self._handlers.pop(name, None)

    # ------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------

    @staticmethod
    def _normalize_event_name(
        event_name: str,
    ) -> str:
        """Normalize event names."""

        if not isinstance(event_name, str):
            raise TypeError(
                "event_name must be a string."
            )

        normalized = event_name.strip().lower()

        if not normalized:
            raise ValueError(
                "event_name cannot be empty."
            )

        return normalized


__all__ = [
    "AKIEvent",
    "EventBus",
    "EventHandler",
]