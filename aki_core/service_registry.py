"""Thread-safe, singleton service registry for AKI.

This module provides a standalone dependency injection container used
to register, resolve, and manage the lifetime of services throughout
AKI. It has no dependency on any other part of the codebase and can be
imported in isolation.

The registry supports three service lifetimes:

* **Instance** -- an already-constructed object is registered directly
  and returned as-is on every resolution.
* **Singleton** -- a factory callable is registered and invoked at most
  once, lazily, on first resolution. The resulting instance is cached
  and reused for all subsequent resolutions.
* **Transient** -- a factory callable is registered and invoked on
  every resolution, producing a new instance each time.

`ServiceRegistry` itself is implemented as a process-wide singleton:
every call to `ServiceRegistry()` returns the same instance. All public
operations are thread-safe.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Generic, TypeVar, cast

__all__ = [
    "ServiceRegistry",
    "ServiceRegistryError",
    "ServiceNotRegisteredError",
    "ServiceAlreadyRegisteredError",
    "ServiceInstantiationError",
]

_logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceLifetime(Enum):
    """Lifecycle strategy governing how a registered service is created.

    Attributes:
        INSTANCE: A concrete object was supplied at registration time
            and is returned unchanged on every resolution.
        SINGLETON: A factory is invoked at most once, lazily, on first
            resolution. The result is cached and reused thereafter.
        TRANSIENT: A factory is invoked on every resolution, producing
            a new instance each time.
    """

    INSTANCE = "instance"
    SINGLETON = "singleton"
    TRANSIENT = "transient"


class ServiceRegistryError(Exception):
    """Base class for all exceptions raised by `ServiceRegistry`."""


class ServiceNotRegisteredError(ServiceRegistryError):
    """Raised when a requested service type has not been registered.

    Attributes:
        service_type: The service type that was requested but not found.
    """

    def __init__(self, service_type: type) -> None:
        """Initialize the exception.

        Args:
            service_type: The service type that was requested but not
                found in the registry.
        """
        self.service_type = service_type
        super().__init__(
            f"Service '{service_type.__name__}' is not registered."
        )


class ServiceAlreadyRegisteredError(ServiceRegistryError):
    """Raised when registering a service type that already exists.

    This is only raised when the caller does not explicitly request an
    overwrite via the `overwrite` keyword argument.

    Attributes:
        service_type: The service type that was already registered.
    """

    def __init__(self, service_type: type) -> None:
        """Initialize the exception.

        Args:
            service_type: The service type that was already registered.
        """
        self.service_type = service_type
        super().__init__(
            f"Service '{service_type.__name__}' is already registered. "
            "Pass overwrite=True to replace the existing registration."
        )


class ServiceInstantiationError(ServiceRegistryError):
    """Raised when a registered factory fails to produce an instance.

    Attributes:
        service_type: The service type whose factory raised an exception.
    """

    def __init__(self, service_type: type, cause: BaseException) -> None:
        """Initialize the exception.

        Args:
            service_type: The service type whose factory raised an
                exception while being resolved.
            cause: The original exception raised by the factory.
        """
        self.service_type = service_type
        super().__init__(
            f"Failed to instantiate service '{service_type.__name__}': {cause}"
        )
        self.__cause__ = cause


@dataclass
class _ServiceRegistration(Generic[T]):
    """Internal bookkeeping record for a single registered service.

    This type is private to the module. Callers interact with services
    exclusively through `ServiceRegistry`'s public API.

    Attributes:
        lifetime: The lifecycle strategy governing this registration.
        factory: The callable used to produce an instance, present for
            `SINGLETON` and `TRANSIENT` lifetimes; `None` for `INSTANCE`.
        instance: The resolved instance. Populated at registration time
            for `INSTANCE`, populated lazily on first resolution for
            `SINGLETON`, and always `None` for `TRANSIENT`.
        lock: A per-registration lock guarding lazy singleton creation,
            so concurrent callers cannot race to build the instance
            more than once.
    """

    lifetime: ServiceLifetime
    factory: Callable[[], T] | None = None
    instance: T | None = None
    lock: threading.Lock = field(
        default_factory=threading.Lock, repr=False, compare=False
    )


class ServiceRegistry:
    """Thread-safe, process-wide singleton dependency injection container.

    `ServiceRegistry` is the central place services are registered and
    resolved from throughout AKI. Every call to `ServiceRegistry()`
    returns the same underlying instance, so any component may obtain
    the registry without it being explicitly passed around.

    All public methods are safe to call concurrently from multiple
    threads. A single reentrant lock guards the registration table
    itself, while each individual registration holds its own lock to
    guard lazy singleton construction -- this allows unrelated services
    to be resolved concurrently without contending on a single lock
    while a factory runs.
    """

    _instance: "ServiceRegistry | None" = None
    _instance_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "ServiceRegistry":
        """Return the process-wide singleton instance.

        Uses double-checked locking so the common case (the instance
        already exists) never pays the cost of acquiring a lock.

        Returns:
            The single shared `ServiceRegistry` instance.
        """
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._bootstrap()
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """No-op initializer.

        All real initialization happens exactly once in `_bootstrap`,
        invoked from `__new__` the first time the singleton is created.
        This override prevents Python from re-running field
        initialization on every `ServiceRegistry()` call.
        """

    def _bootstrap(self) -> None:
        """Initialize internal state. Invoked exactly once per process."""
        self._registrations: dict[type, _ServiceRegistration[Any]] = {}
        self._lock = threading.RLock()
        _logger.debug("ServiceRegistry initialized.")

    def register(
        self, service_type: type[T], instance: T, *, overwrite: bool = False
    ) -> None:
        """Register an already-constructed instance for a service type.

        The supplied instance is returned unchanged on every subsequent
        call to `get(service_type)`.

        Args:
            service_type: The type to register the instance under.
            instance: The concrete object to serve for `service_type`.
            overwrite: If `True`, silently replace an existing
                registration for `service_type` instead of raising.

        Raises:
            ServiceAlreadyRegisteredError: If `service_type` is already
                registered and `overwrite` is `False`.
        """
        registration: _ServiceRegistration[T] = _ServiceRegistration(
            lifetime=ServiceLifetime.INSTANCE, instance=instance
        )
        self._store(service_type, registration, overwrite=overwrite)

    def register_singleton(
        self,
        service_type: type[T],
        factory: Callable[[], T],
        *,
        overwrite: bool = False,
    ) -> None:
        """Register a factory that is lazily invoked at most once.

        `factory` is not called at registration time. It is invoked on
        the first call to `get(service_type)`, and the resulting
        instance is cached and reused for every subsequent resolution.

        Args:
            service_type: The type to register the factory under.
            factory: A zero-argument callable that constructs the
                service instance.
            overwrite: If `True`, silently replace an existing
                registration for `service_type` instead of raising.

        Raises:
            ServiceAlreadyRegisteredError: If `service_type` is already
                registered and `overwrite` is `False`.
        """
        registration: _ServiceRegistration[T] = _ServiceRegistration(
            lifetime=ServiceLifetime.SINGLETON, factory=factory
        )
        self._store(service_type, registration, overwrite=overwrite)

    def register_factory(
        self,
        service_type: type[T],
        factory: Callable[[], T],
        *,
        overwrite: bool = False,
    ) -> None:
        """Register a factory that is invoked on every resolution.

        `factory` is not called at registration time. It is invoked
        once per call to `get(service_type)`, producing a new instance
        each time.

        Args:
            service_type: The type to register the factory under.
            factory: A zero-argument callable that constructs a new
                service instance on each call.
            overwrite: If `True`, silently replace an existing
                registration for `service_type` instead of raising.

        Raises:
            ServiceAlreadyRegisteredError: If `service_type` is already
                registered and `overwrite` is `False`.
        """
        registration: _ServiceRegistration[T] = _ServiceRegistration(
            lifetime=ServiceLifetime.TRANSIENT, factory=factory
        )
        self._store(service_type, registration, overwrite=overwrite)

    def get(self, service_type: type[T]) -> T:
        """Resolve a service instance for the given type.

        Args:
            service_type: The type of service to resolve.

        Returns:
            The resolved service instance. For `INSTANCE` and
            `SINGLETON` lifetimes this is a cached, shared object; for
            `TRANSIENT` lifetimes this is a freshly constructed object.

        Raises:
            ServiceNotRegisteredError: If `service_type` has not been
                registered.
            ServiceInstantiationError: If the registered factory raises
                an exception while constructing the instance.
        """
        with self._lock:
            registration = self._registrations.get(service_type)

        if registration is None:
            raise ServiceNotRegisteredError(service_type)

        if registration.lifetime is ServiceLifetime.INSTANCE:
            return cast(T, registration.instance)

        if registration.lifetime is ServiceLifetime.TRANSIENT:
            return self._instantiate(service_type, registration)

        # SINGLETON: double-checked locking around lazy construction so
        # concurrent callers cannot build two competing instances.
        if registration.instance is None:
            with registration.lock:
                if registration.instance is None:
                    registration.instance = self._instantiate(
                        service_type, registration
                    )
        return cast(T, registration.instance)

    def remove(self, service_type: type[T]) -> None:
        """Unregister a service type.

        Args:
            service_type: The type to remove from the registry.

        Raises:
            ServiceNotRegisteredError: If `service_type` is not
                currently registered.
        """
        with self._lock:
            if service_type not in self._registrations:
                raise ServiceNotRegisteredError(service_type)
            del self._registrations[service_type]
            _logger.debug("Removed service registration: %s", service_type)

    def contains(self, service_type: type[T]) -> bool:
        """Check whether a service type is currently registered.

        Args:
            service_type: The type to check for.

        Returns:
            `True` if `service_type` is registered, `False` otherwise.
        """
        with self._lock:
            return service_type in self._registrations

    def clear(self) -> None:
        """Remove every registration from the registry.

        Existing cached singleton instances are discarded; a
        subsequently re-registered singleton factory will be invoked
        again on its next resolution.
        """
        with self._lock:
            count = len(self._registrations)
            self._registrations.clear()
            _logger.info("Cleared %d service registration(s).", count)

    def services(self) -> tuple[type, ...]:
        """List every currently registered service type.

        Returns:
            A tuple of registered service types, in registration order.
        """
        with self._lock:
            return tuple(self._registrations.keys())

    def _store(
        self,
        service_type: type[T],
        registration: _ServiceRegistration[T],
        *,
        overwrite: bool,
    ) -> None:
        """Insert a registration into the registry table.

        Args:
            service_type: The type being registered.
            registration: The registration record to store.
            overwrite: If `True`, replace an existing registration
                instead of raising.

        Raises:
            ServiceAlreadyRegisteredError: If `service_type` is already
                registered and `overwrite` is `False`.
        """
        with self._lock:
            already_registered = service_type in self._registrations
            if already_registered and not overwrite:
                raise ServiceAlreadyRegisteredError(service_type)

            self._registrations[service_type] = registration

            if already_registered:
                _logger.warning(
                    "Replaced existing registration for %s (lifetime=%s).",
                    service_type,
                    registration.lifetime.value,
                )
            else:
                _logger.debug(
                    "Registered %s (lifetime=%s).",
                    service_type,
                    registration.lifetime.value,
                )

    @staticmethod
    def _instantiate(
        service_type: type[T], registration: _ServiceRegistration[T]
    ) -> T:
        """Invoke a registration's factory and return the result.

        Args:
            service_type: The type being constructed, used for error
                reporting only.
            registration: The registration whose factory should be
                invoked. Must have a non-`None` `factory`.

        Returns:
            The instance produced by the factory.

        Raises:
            ServiceInstantiationError: If the factory raises any
                exception during construction.
        """
        factory = registration.factory
        assert factory is not None  # INSTANCE lifetime never reaches here.
        try:
            return factory()
        except Exception as error:  # noqa: BLE001 - intentionally broad.
            _logger.error(
                "Factory for %s raised during instantiation: %s",
                service_type,
                error,
            )
            raise ServiceInstantiationError(service_type, error) from error

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the registry.

        Returns:
            A string showing how many services are currently registered.
        """
        with self._lock:
            count = len(self._registrations)
        return f"<ServiceRegistry services={count}>"