"""
AKI Confirmation Manager

Manages explicit user confirmation for sensitive actions.

IMPORTANT:
This module does NOT execute commands.
It does NOT access the operating system.
It only creates, tracks, approves, and rejects confirmation requests.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import monotonic
from uuid import uuid4


class ConfirmationStatus(str, Enum):
    """Possible states of a confirmation request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ConfirmationRequest:
    """
    Represents a request waiting for explicit user approval.
    """

    request_id: str
    action: str
    reason: str
    created_at: float
    expires_at: float
    status: ConfirmationStatus = ConfirmationStatus.PENDING


class ConfirmationManager:
    """
    Controls confirmation requests for sensitive AKI actions.

    No system operation is performed here.
    """

    def __init__(self, default_timeout: float = 60.0) -> None:
        if default_timeout <= 0:
            raise ValueError(
                "default_timeout must be greater than zero."
            )

        self._default_timeout = default_timeout
        self._requests: dict[str, ConfirmationRequest] = {}

    @property
    def default_timeout(self) -> float:
        """Return the default confirmation timeout."""

        return self._default_timeout

    def create_request(
        self,
        action: str,
        reason: str,
        timeout: float | None = None,
    ) -> ConfirmationRequest:
        """
        Create a new pending confirmation request.
        """

        action = self._normalize(action)

        if not action:
            raise ValueError("Action cannot be empty.")

        reason = reason.strip()

        if not reason:
            raise ValueError("Confirmation reason cannot be empty.")

        request_timeout = (
            self._default_timeout
            if timeout is None
            else timeout
        )

        if request_timeout <= 0:
            raise ValueError(
                "timeout must be greater than zero."
            )

        now = monotonic()

        request = ConfirmationRequest(
            request_id=str(uuid4()),
            action=action,
            reason=reason,
            created_at=now,
            expires_at=now + request_timeout,
        )

        self._requests[request.request_id] = request

        return request

    def get(
        self,
        request_id: str,
    ) -> ConfirmationRequest | None:
        """
        Retrieve a confirmation request.

        Expired pending requests are automatically marked expired.
        """

        request = self._requests.get(request_id)

        if request is None:
            return None

        if (
            request.status == ConfirmationStatus.PENDING
            and monotonic() >= request.expires_at
        ):
            request = self._update_status(
                request,
                ConfirmationStatus.EXPIRED,
            )

        return request

    def approve(
        self,
        request_id: str,
    ) -> ConfirmationRequest:
        """
        Approve a pending confirmation request.

        Approval only changes state.
        It does NOT execute the action.
        """

        request = self._require_pending(request_id)

        request = self._update_status(
            request,
            ConfirmationStatus.APPROVED,
        )

        return request

    def reject(
        self,
        request_id: str,
    ) -> ConfirmationRequest:
        """
        Reject a pending confirmation request.
        """

        request = self._require_pending(request_id)

        request = self._update_status(
            request,
            ConfirmationStatus.REJECTED,
        )

        return request

    def cancel(
        self,
        request_id: str,
    ) -> ConfirmationRequest:
        """
        Cancel a pending confirmation request.
        """

        request = self._require_pending(request_id)

        request = self._update_status(
            request,
            ConfirmationStatus.CANCELLED,
        )

        return request

    def is_approved(self, request_id: str) -> bool:
        """Return True only when the request was explicitly approved."""

        request = self.get(request_id)

        return (
            request is not None
            and request.status == ConfirmationStatus.APPROVED
        )

    def is_pending(self, request_id: str) -> bool:
        """Return True when the request is still waiting for confirmation."""

        request = self.get(request_id)

        return (
            request is not None
            and request.status == ConfirmationStatus.PENDING
        )

    def cleanup(self) -> None:
        """
        Mark expired pending requests as expired.

        Completed requests remain available for audit/history.
        """

        now = monotonic()

        for request_id, request in tuple(self._requests.items()):
            if (
                request.status == ConfirmationStatus.PENDING
                and now >= request.expires_at
            ):
                self._requests[request_id] = (
                    self._update_status(
                        request,
                        ConfirmationStatus.EXPIRED,
                    )
                )

    def clear(self) -> None:
        """Remove all stored confirmation requests."""

        self._requests.clear()

    def _require_pending(
        self,
        request_id: str,
    ) -> ConfirmationRequest:
        """Return a pending request or raise a clear error."""

        request = self.get(request_id)

        if request is None:
            raise KeyError(
                f"Unknown confirmation request: {request_id}"
            )

        if request.status != ConfirmationStatus.PENDING:
            raise ValueError(
                f"Confirmation request is already "
                f"{request.status.value}."
            )

        return request

    def _update_status(
        self,
        request: ConfirmationRequest,
        status: ConfirmationStatus,
    ) -> ConfirmationRequest:
        """Create an updated immutable request."""

        updated = ConfirmationRequest(
            request_id=request.request_id,
            action=request.action,
            reason=request.reason,
            created_at=request.created_at,
            expires_at=request.expires_at,
            status=status,
        )

        self._requests[request.request_id] = updated

        return updated

    @staticmethod
    def _normalize(action: str) -> str:
        """Normalize an action name."""

        if not isinstance(action, str):
            raise TypeError(
                "Action must be a string."
            )

        return action.strip().lower()


__all__ = [
    "ConfirmationManager",
    "ConfirmationRequest",
    "ConfirmationStatus",
]