"""
AKI Telemetry Service.

Collects real system and application telemetry for AKI.

This service is responsible for observing system resources.
It does not execute operating-system actions and does not invent
AI, memory, or automation health values.

External subsystem status can be supplied through providers later
without changing the telemetry API consumed by the desktop layer.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Callable

import psutil


logger = logging.getLogger(__name__)

_BYTES_PER_MB = 1024 * 1024
_BYTES_PER_GB = 1024 * 1024 * 1024


# ================================================================
# Provider Contracts
# ================================================================

StatusProvider = Callable[[], dict[str, Any]]


# ================================================================
# Telemetry Snapshot
# ================================================================


@dataclass(frozen=True)
class TelemetrySnapshot:
    """
    Immutable telemetry snapshot.

    The desktop layer can convert this object to a dictionary
    without depending on the internal implementation.
    """

    timestamp: float
    uptime_seconds: int
    uptime: str
    system: dict[str, Any]
    ai_core: dict[str, Any]
    memory_subsystem: dict[str, Any]
    automation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return the snapshot as a serializable dictionary."""

        return {
            "timestamp": self.timestamp,
            "uptime": self.uptime,
            "uptime_seconds": self.uptime_seconds,
            "system": dict(self.system),
            "ai_core": dict(self.ai_core),
            "memory_subsystem": dict(self.memory_subsystem),
            "automation": dict(self.automation),
        }


# ================================================================
# Telemetry Service
# ================================================================


class TelemetryService:
    """
    Collect real system and application telemetry.

    System metrics are collected directly through psutil.

    AI, memory, and automation status are intentionally provider-based.
    If no provider is registered, their state is reported as
    ``UNKNOWN`` rather than pretending that the subsystem is healthy.
    """

    def __init__(
        self,
        *,
        ai_status_provider: StatusProvider | None = None,
        memory_status_provider: StatusProvider | None = None,
        automation_status_provider: StatusProvider | None = None,
    ) -> None:
        self._start_time = time.monotonic()

        self._process = psutil.Process(os.getpid())

        self._ai_status_provider = ai_status_provider
        self._memory_status_provider = memory_status_provider
        self._automation_status_provider = automation_status_provider

    # ============================================================
    # Uptime
    # ============================================================

    def get_system_uptime_seconds(self) -> int:
        """
        Return AKI application uptime in seconds.

        Uses ``monotonic()`` so system clock changes do not affect
        the uptime calculation.
        """

        return int(time.monotonic() - self._start_time)

    def get_formatted_uptime(self) -> str:
        """Return application uptime as HH:MM:SS."""

        uptime_seconds = self.get_system_uptime_seconds()

        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    # ============================================================
    # Provider Configuration
    # ============================================================

    def set_ai_status_provider(
        self,
        provider: StatusProvider | None,
    ) -> None:
        """Set or remove the AI subsystem status provider."""

        self._ai_status_provider = provider

    def set_memory_status_provider(
        self,
        provider: StatusProvider | None,
    ) -> None:
        """Set or remove the memory subsystem status provider."""

        self._memory_status_provider = provider

    def set_automation_status_provider(
        self,
        provider: StatusProvider | None,
    ) -> None:
        """Set or remove the automation subsystem status provider."""

        self._automation_status_provider = provider

    # ============================================================
    # Snapshot
    # ============================================================

    def get_snapshot(self) -> TelemetrySnapshot:
        """
        Collect a complete telemetry snapshot.

        Returns:
            A TelemetrySnapshot containing real system metrics and
            provider-backed subsystem information.
        """

        try:
            cpu_percent = psutil.cpu_percent(interval=None)

            virtual_memory = psutil.virtual_memory()

            process_memory = self._process.memory_info()

            logical_cpu_count = psutil.cpu_count(
                logical=True
            ) or 1

            process_count = len(
                list(psutil.process_iter())
            )

            return TelemetrySnapshot(
                timestamp=time.time(),
                uptime_seconds=self.get_system_uptime_seconds(),
                uptime=self.get_formatted_uptime(),
                system={
                    "cpu_percent": round(cpu_percent, 1),
                    "cpu_count": logical_cpu_count,
                    "ram_percent": round(
                        virtual_memory.percent,
                        1,
                    ),
                    "ram_used_gb": round(
                        virtual_memory.used / _BYTES_PER_GB,
                        2,
                    ),
                    "ram_total_gb": round(
                        virtual_memory.total / _BYTES_PER_GB,
                        2,
                    ),
                    "process_ram_mb": round(
                        process_memory.rss / _BYTES_PER_MB,
                        1,
                    ),
                    "process_count": process_count,
                    "status_label": self._system_status(
                        cpu_percent
                    ),
                },
                ai_core=self._get_provider_status(
                    self._ai_status_provider
                ),
                memory_subsystem=self._get_provider_status(
                    self._memory_status_provider
                ),
                automation=self._get_provider_status(
                    self._automation_status_provider
                ),
            )

        except Exception:
            logger.exception(
                "Failed to collect AKI telemetry."
            )

            return TelemetrySnapshot(
                timestamp=time.time(),
                uptime_seconds=self.get_system_uptime_seconds(),
                uptime=self.get_formatted_uptime(),
                system={
                    "cpu_percent": 0.0,
                    "cpu_count": 0,
                    "ram_percent": 0.0,
                    "ram_used_gb": 0.0,
                    "ram_total_gb": 0.0,
                    "process_ram_mb": 0.0,
                    "process_count": 0,
                    "status_label": "ERROR",
                },
                ai_core={
                    "status": "UNKNOWN",
                },
                memory_subsystem={
                    "status": "UNKNOWN",
                },
                automation={
                    "status": "UNKNOWN",
                },
            )

    # ============================================================
    # Dictionary API
    # ============================================================

    def get_telemetry_snapshot(self) -> dict[str, Any]:
        """
        Return telemetry in dictionary form.

        This method preserves the API expected by the desktop
        presentation layer.
        """

        return self.get_snapshot().to_dict()

    # ============================================================
    # System Status
    # ============================================================

    @staticmethod
    def _system_status(
        cpu_percent: float,
    ) -> str:
        """Convert CPU utilization into a simple status label."""

        if cpu_percent >= 90:
            return "HIGH LOAD"

        if cpu_percent >= 70:
            return "ELEVATED"

        return "NOMINAL"

    # ============================================================
    # Provider Status
    # ============================================================

    @staticmethod
    def _get_provider_status(
        provider: StatusProvider | None,
    ) -> dict[str, Any]:
        """
        Safely obtain subsystem status from a provider.

        No provider means the real state is currently unknown.
        """

        if provider is None:
            return {
                "status": "UNKNOWN",
            }

        try:
            result = provider()

            if not isinstance(result, dict):
                logger.warning(
                    "Telemetry provider returned "
                    "an invalid result."
                )

                return {
                    "status": "UNKNOWN",
                }

            return dict(result)

        except Exception:
            logger.exception(
                "Telemetry provider failed."
            )

            return {
                "status": "ERROR",
            }


__all__ = [
    "StatusProvider",
    "TelemetryService",
    "TelemetrySnapshot",
]