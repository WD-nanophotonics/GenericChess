"""Register and review disposable workspace paths before explicit deletion.

The registry is local runtime data. Registering or approving never deletes files.
Only ``execute --confirm DELETE_REGISTERED`` can remove approved, unchanged paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
REGISTRY_NAME = ".generic_chess_flow/safe_cleanup_registry.json"
PROTECTED_PARTS = {".git", ".generic_chess_flow", ".courier_outbox", ".venv"}


def _reparse(path: Path) -> bool:
    info = path.lstat()
    return path.is_symlink() or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


class CleanupRegistry:
    def __init__(self, workspace: Path = WORKSPACE):
        self.workspace = workspace.resolve(strict=True)
        self.registry_path = self.workspace / REGISTRY_NAME

    def _target(self, name: str) -> tuple[str, Path]:
        relative = Path(name)
        if (not name or relative.is_absolute() or relative.drive or relative.anchor
                or not relative.parts
                or any(part in {"", ".", ".."} for part in relative.parts)
                or any(part.lower() in PROTECTED_PARTS for part in relative.parts)):
            raise ValueError(f"Unsafe relative path: {name!r}")
        current = self.workspace
        for part in relative.parts:
            current = current / part
            if not current.exists() or _reparse(current):
                raise ValueError(f"Missing path or reparse point: {current}")
        resolved = current.resolve(strict=True)
        if resolved == self.workspace or not resolved.is_relative_to(self.workspace):
            raise ValueError("Target must stay inside the workspace")
        return relative.as_posix(), current

    def _snapshot(self, path: Path) -> dict:
        digest = hashlib.sha256()
        files = 0
        bytes_count = 0

        def visit(item: Path) -> None:
            nonlocal files, bytes_count
            if _reparse(item):
                raise ValueError(f"Reparse point in tree: {item}")
            name = item.relative_to(path).as_posix()
            if item.is_dir():
                digest.update(f"D\0{name}\0".encode())
                for child in sorted(item.iterdir(), key=lambda p: p.name):
                    visit(child)
            elif item.is_file():
                size = item.stat().st_size
                files += 1
                bytes_count += size
                digest.update(f"F\0{name}\0{size}\0".encode())
                with item.open("rb") as stream:
                    while chunk := stream.read(1024 * 1024):
                        digest.update(chunk)
            else:
                raise ValueError(f"Unsupported file type: {item}")

        visit(path)
        return {
            "kind": "directory" if path.is_dir() else "file",
            "sha256": digest.hexdigest(),
            "files": files,
            "bytes": bytes_count,
        }

    def _load(self) -> dict:
        if not self.registry_path.exists():
            return {"version": 1, "entries": {}}
        data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        if data.get("version") != 1 or not isinstance(data.get("entries"), dict):
            raise ValueError("Unsupported cleanup registry")
        return data

    def _save(self, data: dict) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.registry_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(temporary, self.registry_path)

    def register(self, name: str, reason: str) -> dict:
        if not reason.strip():
            raise ValueError("A reason is required")
        key, target = self._target(name)
        data = self._load()
        entry = {
            "reason": reason.strip(),
            "snapshot": self._snapshot(target),
            "approved": False,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        data["entries"][key] = entry
        self._save(data)
        return entry

    def approve(self, name: str) -> None:
        key, target = self._target(name)
        data = self._load()
        entry = data["entries"].get(key)
        if entry is None or entry.get("deleted_at"):
            raise ValueError(f"Not a registered live candidate: {key}")
        if self._snapshot(target) != entry["snapshot"]:
            raise ValueError(f"Candidate changed since registration: {key}")
        entry["approved"] = True
        entry["approved_at"] = datetime.now(timezone.utc).isoformat()
        self._save(data)

    def list_entries(self) -> list[dict]:
        result = []
        for name, entry in self._load()["entries"].items():
            if entry.get("deleted_at"):
                state = "deleted"
            else:
                try:
                    _, target = self._target(name)
                    state = "ready" if self._snapshot(target) == entry["snapshot"] else "changed"
                except (OSError, ValueError):
                    state = "missing-or-unsafe"
            result.append({"path": name, "state": state,
                           "approved": entry["approved"], "reason": entry["reason"],
                           **entry["snapshot"]})
        return result

    def execute(self, confirmation: str) -> list[str]:
        if confirmation != "DELETE_REGISTERED":
            raise ValueError("Pass --confirm DELETE_REGISTERED to delete approved entries")
        data = self._load()
        ready = []
        for name, entry in data["entries"].items():
            if not entry["approved"] or entry.get("deleted_at"):
                continue
            _, target = self._target(name)
            if self._snapshot(target) != entry["snapshot"]:
                raise ValueError(f"Candidate changed; nothing deleted: {name}")
            ready.append((name, target))
        # All candidates are checked before any deletion. Never delete overlapping trees.
        names = [name for name, _ in ready]
        for index, name in enumerate(names):
            if any(name.startswith(other + "/") for other in names[:index] + names[index + 1:]):
                raise ValueError(f"Overlapping registered paths; nothing deleted: {name}")
        deleted = []
        for name, target in ready:
            # Recheck immediately before removal in case files changed during execution.
            if self._snapshot(target) != data["entries"][name]["snapshot"]:
                raise ValueError(f"Candidate changed; skipped: {name}")
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            data["entries"][name]["deleted_at"] = datetime.now(timezone.utc).isoformat()
            self._save(data)
            deleted.append(name)
        return deleted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("list", help="Preview registered candidates and current safety checks")
    register = actions.add_parser("register", help="Register a candidate without approving deletion")
    register.add_argument("path", help="Path relative to the GenericChess-sandbox root")
    register.add_argument("--reason", required=True)
    approve = actions.add_parser("approve", help="Approve an unchanged registered candidate")
    approve.add_argument("path")
    execute = actions.add_parser("execute", help="Delete approved unchanged candidates")
    execute.add_argument("--confirm", required=True, help="Must equal DELETE_REGISTERED")
    args = parser.parse_args(argv)
    registry = CleanupRegistry()
    try:
        if args.action == "register":
            print(json.dumps(registry.register(args.path, args.reason), ensure_ascii=False, indent=2))
        elif args.action == "approve":
            registry.approve(args.path)
            print(f"Approved: {args.path}")
        elif args.action == "execute":
            print(json.dumps({"deleted": registry.execute(args.confirm)}, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(registry.list_entries(), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Cleanup refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
