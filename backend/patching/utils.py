from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from uuid import uuid4

PATCH_HEADER = "*** Begin Patch"
PATCH_FOOTER = "*** End Patch"


@dataclass(slots=True)
class RollbackMetadata:
    file_path: str
    patch_id: str
    backup_path: str
    rollback_hint: str


def validate_patch(patch_text: str) -> bool:
    """Minimal structural validation for patch envelopes."""
    if not patch_text or not patch_text.strip():
        return False
    stripped = patch_text.strip()
    return stripped.startswith(PATCH_HEADER) and stripped.endswith(PATCH_FOOTER)


def render_preview(patch_text: str, max_lines: int = 200) -> str:
    """Returns a truncated preview safe for manual review."""
    lines = patch_text.splitlines()
    if len(lines) <= max_lines:
        return patch_text
    preview = "\n".join(lines[:max_lines])
    return f"{preview}\n...\n[preview truncated: total_lines={len(lines)}]"


def _backup_file(src: Path, temp_dir: Path, patch_id: str) -> Path:
    temp_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_name = f"{src.name}.{patch_id}.{timestamp}.bak"
    backup_path = temp_dir / backup_name
    shutil.copy2(src, backup_path)
    return backup_path


def apply_patch(
    file_path: str,
    patched_content: str,
    *,
    approved: bool,
    patch_id: str | None = None,
    temp_dir: str = "temp",
    patches_dir: str = "patches",
) -> RollbackMetadata:
    """Applies content replacement only after approval.

    All writes are staged into temp/ and patches/ first.
    """
    if not approved:
        raise PermissionError("Patch application is blocked until manual approval is granted.")

    patch_id = patch_id or str(uuid4())
    target = Path(file_path)
    temp_root = Path(temp_dir)
    patches_root = Path(patches_dir)

    if not target.exists():
        raise FileNotFoundError(f"Target file not found: {file_path}")

    backup_path = _backup_file(target, temp_root, patch_id)

    staged_content_path = temp_root / f"{target.name}.{patch_id}.staged"
    staged_content_path.write_text(patched_content, encoding="utf-8")

    # Persist patch artifact/metadata before changing the target file.
    patches_root.mkdir(parents=True, exist_ok=True)
    patch_record_path = patches_root / f"{patch_id}.json"
    patch_record = {
        "patch_id": patch_id,
        "file_path": str(target),
        "staged_content_path": str(staged_content_path),
        "backup_path": str(backup_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    patch_record_path.write_text(json.dumps(patch_record, ensure_ascii=False, indent=2), encoding="utf-8")

    target.write_text(staged_content_path.read_text(encoding="utf-8"), encoding="utf-8")

    rollback_hint = f"cp '{backup_path}' '{target}'"
    metadata = RollbackMetadata(
        file_path=str(target),
        patch_id=patch_id,
        backup_path=str(backup_path),
        rollback_hint=rollback_hint,
    )

    rollback_index = patches_root / "rollback_index.jsonl"
    with rollback_index.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(metadata.__dict__, ensure_ascii=False) + "\n")

    return metadata
