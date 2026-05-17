from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from uuid import uuid4

from .utils import (
    RollbackMetadata,
    apply_patch,
    calculate_sha256,
    render_preview,
    validate_patch_semantics,
    validate_patch_structure,
)


@dataclass(slots=True)
class DiffPatchPipeline:
    """Pipeline for building/staging patch artifacts before application."""

    temp_dir: str = "temp"
    patches_dir: str = "patches"
    context_lines: int = 3

    def generate(self, original_text: str, patched_text: str) -> dict[str, str]:
        patch_id = str(uuid4())

        original_lines = original_text.splitlines(keepends=True)
        patched_lines = patched_text.splitlines(keepends=True)
        diff_lines = list(difflib.unified_diff(
            original_lines,
            patched_lines,
            fromfile="target (original)",
            tofile="target (patched)",
            n=self.context_lines,
        ))

        if not diff_lines:
            raise ValueError("No differences detected between original and patched content.")

        patch_body = "*** Begin Patch\n*** Update File: target\n" + "".join(diff_lines) + "*** End Patch\n"

        artifact_path = Path(self.patches_dir)
        artifact_path.mkdir(parents=True, exist_ok=True)
        patch_file = artifact_path / f"{patch_id}.patch"
        patch_file.write_text(patch_body, encoding="utf-8")

        return {"patch_id": patch_id, "patch_text": patch_body, "patch_file": str(patch_file)}


@dataclass(slots=True)
class ManualApprovalPipeline:
    """Validates and previews patch, then applies only if approved."""

    temp_dir: str = "temp"
    patches_dir: str = "patches"

    def process(
        self,
        *,
        file_path: str,
        patch_text: str,
        patched_content: str,
        is_approved: Callable[[str], bool],
        patch_id: str | None = None,
    ) -> RollbackMetadata:
        target = Path(file_path)
        if not target.exists():
            raise FileNotFoundError(f"Target file not found: {file_path}")

        original_content = target.read_text(encoding="utf-8")
        original_sha256 = calculate_sha256(original_content)

        if not validate_patch_structure(patch_text):
            raise ValueError("Patch structural validation failed.")
        if not validate_patch_semantics(
            patch_text,
            expected_original=original_content,
            patched_content=patched_content,
        ):
            raise ValueError("Patch semantic validation failed.")

        preview = render_preview(patch_text)
        approved = is_approved(preview)
        if not approved:
            raise PermissionError("Patch application is blocked until manual approval is granted.")

        if calculate_sha256(original_content) != original_sha256:
            raise ValueError("Preview content checksum mismatch before apply.")

        return apply_patch(
            file_path=file_path,
            patched_content=patched_content,
            approved=True,
            patch_id=patch_id,
            temp_dir=self.temp_dir,
            patches_dir=self.patches_dir,
            expected_original_sha256=original_sha256,
        )
