from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from uuid import uuid4

from .utils import RollbackMetadata, apply_patch, render_preview, validate_patch


@dataclass(slots=True)
class DiffPatchPipeline:
    """Pipeline for building/staging patch artifacts before application."""

    temp_dir: str = "temp"
    patches_dir: str = "patches"

    def generate(self, original_text: str, patched_text: str) -> dict[str, str]:
        patch_id = str(uuid4())
        patch_body = (
            "*** Begin Patch\n"
            "*** Update File: target\n"
            "@@\n"
            f"- {original_text[:120]}\n"
            f"+ {patched_text[:120]}\n"
            "*** End Patch\n"
        )

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
        if not validate_patch(patch_text):
            raise ValueError("Patch validation failed.")

        preview = render_preview(patch_text)
        approved = is_approved(preview)

        return apply_patch(
            file_path=file_path,
            patched_content=patched_content,
            approved=approved,
            patch_id=patch_id,
            temp_dir=self.temp_dir,
            patches_dir=self.patches_dir,
        )
