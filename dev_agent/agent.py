"""
AKI Dev Agent.

Turns natural-language descriptions into real, working project
folders on disk. The AI writes the code; the agent structures it
into files, validates the output, and reports exactly what was built.

Supported project kinds:
    website   — multi-file static site (HTML/CSS/JS)
    python    — standalone Python application
    api       — Flask REST API
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from logs.logger import get_logger

logger = get_logger("dev_agent.agent")

_PROJECTS_ROOT = Path.home() / "Documents" / "AKI_Projects"

_FILE_BLOCK = re.compile(
    r"===FILE:\s*(?P<path>[\w./\\-]+)\s*===\s*\n(?P<content>.*?)===END===",
    re.DOTALL,
)

_FENCE = re.compile(r"```[\w]*\n(.*?)```", re.DOTALL)

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9_-]+")


@dataclass(frozen=True)
class ProjectResult:
    """Outcome of one generated project."""

    name: str
    kind: str
    path: str
    files: tuple[str, ...] = field(default_factory=tuple)

    def summary(self) -> str:
        """Human-readable creation summary."""

        file_lines = "\n".join(f"  - {name}" for name in self.files)

        return (
            f"Project **{self.name}** ready ✅\n"
            f"Type: {self.kind}\n"
            f"Location: `{self.path}`\n"
            f"Files:\n{file_lines}"
        )


class DevAgentError(Exception):
    """Raised when a project cannot be generated."""


class DevAgent:
    """
    JARVIS-style build agent.

    Responsibilities:
        - Build the code-generation prompt for a project kind.
        - Parse the model's multi-file reply safely.
        - Write the project folder to disk (never outside the
          projects root).
        - List previously generated projects.
    """

    KINDS = ("website", "python", "api")

    def __init__(
        self,
        ai_responder: Callable[..., Any],
        projects_root: Path | None = None,
    ) -> None:
        """
        Args:
            ai_responder: Callable(prompt) -> str backed by AIService.
            projects_root: Where projects are written; defaults to
                Documents/AKI_Projects.
        """

        self._ai_responder = ai_responder
        self._projects_root = Path(projects_root or _PROJECTS_ROOT)

    @property
    def projects_root(self) -> Path:
        """Return the folder that holds generated projects."""

        return self._projects_root

    def create_project(
        self,
        *,
        kind: str = "",
        name: str = "",
        description: str,
    ) -> ProjectResult:
        """
        Generate one complete project.

        `kind` and `name` are optional — the agent detects the kind
        from the description and derives a folder name automatically.

        Raises:
            DevAgentError: On bad input, AI failure, or unparseable output.
        """

        kind = self.detect_kind(description) if not kind.strip() else kind.strip().lower()

        if kind not in self.KINDS:
            raise DevAgentError(
                f"Unknown project kind '{kind}'. Options: {', '.join(self.KINDS)}"
            )

        derived_name = self.derive_name(description) if not name.strip() else name.strip()
        clean_name = _SAFE_NAME.sub("_", derived_name)[:40] or "project"
        description = description.strip()

        if not description:
            raise DevAgentError(
                "Description khali hai — batao kya banana hai."
            )

        prompt = self._build_prompt(kind, clean_name, description)

        try:
            reply = str(self._ai_responder(prompt))
        except Exception as error:
            raise DevAgentError(
                f"AI code generation failed: {error}"
            ) from error

        files = self._parse_files(reply)

        if not files:
            raise DevAgentError(
                "AI ne koi valid file nahi banayi — dobara koshish karein."
            )

        project_path = self._write_files(clean_name, files)

        logger.info(
            "Project created | %s (%s) -> %d files",
            clean_name,
            kind,
            len(files),
        )

        return ProjectResult(
            name=clean_name,
            kind=kind,
            path=str(project_path),
            files=tuple(sorted(files.keys())),
        )

    @staticmethod
    def detect_kind(description: str) -> str:
        """
        Infer project type from the instruction itself — the user
        should never need to pick from a dropdown.
        """

        lowered = description.lower()

        if any(word in lowered for word in ("api", "endpoint", "rest", "flask", "server")):
            return "api"

        if any(
            word in lowered
            for word in ("website", "site", "web ", "webpage", "web page", "landing", "portfolio")
        ):
            return "website"

        return "python"

    @staticmethod
    def derive_name(description: str) -> str:
        """Derive a short folder name from the instruction."""

        words = re.findall(r"[a-zA-Z]{3,}", description.lower())

        stopwords = {
            "banao", "bana", "banana", "chahiye", "mujhe", "make", "create",
            "build", "need", "want", "with", "that", "this", "have", "for",
            "the", "and", "website", "app", "application", "project",
        }

        meaningful = [word for word in words if word not in stopwords][:3]
        base = "_".join(meaningful) if meaningful else "project"

        from datetime import datetime

        stamp = datetime.now().strftime("%m%d_%H%M")

        return f"{base}_{stamp}"

    def list_projects(self) -> list[dict[str, Any]]:
        """Return previously generated projects."""

        if not self._projects_root.exists():
            return []

        projects = []

        for folder in sorted(self._projects_root.iterdir()):
            if not folder.is_dir():
                continue

            files = [
                str(item.relative_to(folder))
                for item in folder.rglob("*")
                if item.is_file()
            ]

            projects.append(
                {
                    "name": folder.name,
                    "path": str(folder),
                    "file_count": len(files),
                }
            )

        return projects

    # ============================================================
    # Internals
    # ============================================================

    def _build_prompt(self, kind: str, name: str, description: str) -> str:
        """Kind-specific code-generation prompt."""

        requirements = {
            "website": (
                "a complete, modern, responsive static website. Include "
                "polished CSS (dark glass style), real content sections, "
                "and working JavaScript interactions. 3 files minimum."
            ),
            "python": (
                "a complete, runnable Python application with a CLI or "
                "simple interface, proper functions, error handling, and "
                "a __main__ guard. Include requirements.txt if needed."
            ),
            "api": (
                "a complete Flask REST API with multiple endpoints, JSON "
                "responses, error handling, and a requirements.txt. Keep "
                "it runnable with `python app.py`."
            ),
        }[kind]

        return (
            f"You are AKI DEV, an expert developer agent. Build {requirements}\n\n"
            f"Project name: {name}\n"
            f"Requirements: {description}\n\n"
            "Reply with EVERY file in exactly this format (no other prose):\n"
            "===FILE: filename.ext===\n"
            "<full file content>\n"
            "===END===\n\n"
            "Rules: complete working code, no placeholders, no TODOs, "
            "no explanations outside the file blocks."
        )

    def _parse_files(self, reply: str) -> dict[str, str]:
        """Extract ===FILE: blocks from the model reply."""

        files: dict[str, str] = {}

        for match in _FILE_BLOCK.finditer(reply):
            raw_path = match.group("path").strip().lstrip("/\\")
            content = match.group("content").strip("\n")

            # Strip accidental markdown fences inside content.
            fenced = _FENCE.search(content)

            if fenced and fenced.group(1).strip():
                content = fenced.group(1).rstrip()

            safe_path = self._safe_relative(raw_path)

            if safe_path and content:
                files[safe_path] = content

        return files

    def _write_files(
        self,
        name: str,
        files: dict[str, str],
    ) -> Path:
        """Write files inside the projects root; block path escapes."""

        project_path = (self._projects_root / name).resolve()

        if self._projects_root.resolve() not in project_path.parents:
            raise DevAgentError(
                "Project path projects root ke bahar ja raha hai."
            )

        project_path.mkdir(parents=True, exist_ok=True)

        for relative, content in files.items():
            target = (project_path / relative).resolve()

            if project_path not in target.parents and target.parent != project_path:
                logger.warning("Skipped unsafe path: %s", relative)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        return project_path

    @staticmethod
    def _safe_relative(raw_path: str) -> str:
        """Normalize a model-provided path; reject escapes."""

        cleaned = raw_path.replace("\\", "/").strip()

        # Reject traversal BEFORE stripping so "../../x" never
        # gets silently rewritten into a safe-looking path.
        if ".." in cleaned or cleaned.startswith("/"):
            return ""

        cleaned = cleaned.strip("./")

        if not cleaned or ".." in cleaned:
            return ""

        return cleaned


__all__ = [
    "DevAgent",
    "DevAgentError",
    "ProjectResult",
]
