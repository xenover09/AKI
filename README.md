# AKI — Personal AI Operating Ecosystem

AKI is a next-generation Personal AI Operating Ecosystem inspired by JARVIS and
EDITH. This repository is at the **foundation stage**: only the boot sequence,
configuration, and logging infrastructure exist. No AI, chatbot, voice,
memory, plugin, or automation systems have been implemented yet.

## Tech Stack

- Python 3.12
- PySide6 (introduced when the Presentation layer is built)
- SQLite (introduced when the Infrastructure/persistence layer is built)
- Clean Architecture, PEP8, type hints, docstrings
- Dependency Injection, Repository Pattern, Service Layer

## Architecture

AKI follows Clean Architecture with a strict, one-directional dependency
flow:

```
Presentation
    v
Application
    v
Domain
    v
Infrastructure
```

None of the four layers exist as dedicated packages yet — this stage only
implements the **composition root**, the code responsible for wiring the
application together at startup. A composition root sits outside the four
layers by definition: it is allowed to depend on all of them so it can
assemble the object graph, but no layer is allowed to depend on it.

| Package/File            | Role                                             |
|--------------------------|---------------------------------------------------|
| `config/`                | Cross-cutting configuration (constants + settings) |
| `logs/logger.py`         | Cross-cutting logging infrastructure               |
| `aki_core/`              | Composition root (Boot Manager + Application)      |
| `main.py`                | Process entry point                                |

As the Domain, Application, Infrastructure, and Presentation layers are
implemented module by module, they will live in their own top-level
packages (e.g. `domain/`, `application/`, `infrastructure/`,
`presentation/`), and `aki_core` will wire them together instead of
containing logic itself.

## Boot Sequence

```
main.py
   |
   v
Application
   |
   v
Boot Manager
   |
   v
Configuration   (Settings.load)
   |
   v
Logger          (configure_logging)
   |
   v
Ready
```

1. `main.py` resolves the project root and constructs `Application`.
2. `Application.run()` triggers `BootManager.boot()`.
3. `BootManager` loads `Settings` from environment variables / `.env`.
4. `BootManager` configures the root "AKI" logger using those settings.
5. `BootManager` returns a `BootResult` (settings + logger) to `Application`.
6. `Application` logs `"AKI is Ready."` and returns exit code `0`.

## Setup

1. Create and activate a virtual environment (Python 3.12).
2. Install dependencies:
   ```
   pip install python-dotenv PySide6
   ```
3. Create a `.env` file in the project root (never commit this file):
   ```
   AKI_ENVIRONMENT=development
   AKI_LOG_LEVEL=DEBUG
   AKI_LOG_DIR=runtime/logs
   AKI_DEBUG=true
   ```
4. Run AKI:
   ```
   python main.py
   ```

On success, you will see a startup log line in the console and in
`runtime/logs/aki.log` confirming `"AKI is Ready."`.

## Environment Variables

| Variable          | Default              | Description                          |
|--------------------|-----------------------|---------------------------------------|
| `AKI_ENVIRONMENT`  | `development`         | Deployment environment name           |
| `AKI_LOG_LEVEL`    | `INFO`                | Minimum log severity                  |
| `AKI_LOG_DIR`      | `runtime/logs`        | Log file directory (relative or absolute) |
| `AKI_DEBUG`        | `false`               | Enables debug mode                    |

## Status

Foundation only. Domain, Application (use cases), Infrastructure
(persistence), and Presentation (PySide6 GUI) layers are intentionally not
yet implemented and will be added one module at a time, with explicit
confirmation before each step.

## Author 

Xenover ! 
