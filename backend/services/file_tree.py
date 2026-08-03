"""Bounded, symlink-safe lazy listings for shell home directories."""
from __future__ import annotations

import json
import stat
import time
from pathlib import Path, PurePosixPath


CONTAINER_HOME = PurePosixPath('/home/user')
MAX_RELATIVE_DEPTH = 16
MAX_IMMEDIATE_ITEMS = 200
MAX_SERIALIZED_BYTES = 64 * 1024
MAX_WALL_TIME_SECONDS = 0.25


class FileTreeError(Exception):
    """A controlled error that can safely be returned by the HTTP route."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def build_lazy_tree(user_root: Path, requested_path: str = '/home/user') -> dict:
    """Return one directory node and its direct, non-symlink children only."""
    started = time.monotonic()
    relative_parts = _relative_parts(requested_path)
    root = _checked_root(user_root)
    candidate = root.joinpath(*relative_parts)

    # Resolve before accessing the target, then independently lstat every path
    # component.  Both checks are required: resolve catches containment escapes,
    # while lstat makes following a symlink impossible.
    try:
        resolved_candidate = candidate.resolve(strict=False)
    except OSError as exc:
        raise FileTreeError(400, 'Invalid path') from exc
    try:
        resolved_candidate.relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise FileTreeError(403, 'Path is not available') from exc

    current = root
    for part in relative_parts:
        _check_time(started)
        current = current / part
        _require_directory(current)
    _check_time(started)

    container_path = str(CONTAINER_HOME.joinpath(*relative_parts))
    children = _direct_children(current, root, started)
    node = {
        'name': CONTAINER_HOME.name if not relative_parts else relative_parts[-1],
        'path': container_path,
        'type': 'directory',
        'children': children,
    }
    _check_serialized_size(node)
    _check_time(started)
    return node


def _relative_parts(requested_path: str) -> tuple[str, ...]:
    if not isinstance(requested_path, str):
        raise FileTreeError(400, 'Invalid path')
    path = PurePosixPath(requested_path)
    if not path.is_absolute() or '..' in path.parts or '.' in path.parts:
        raise FileTreeError(400, 'Invalid path')
    try:
        relative = path.relative_to(CONTAINER_HOME)
    except ValueError as exc:
        raise FileTreeError(403, 'Path is not available') from exc
    parts = relative.parts
    if len(parts) > MAX_RELATIVE_DEPTH:
        raise FileTreeError(422, 'Path exceeds listing limits')
    return parts


def _checked_root(user_root: Path) -> Path:
    root = Path(user_root)
    _require_directory(root)
    try:
        return root.resolve(strict=True)
    except OSError as exc:
        raise FileTreeError(400, 'Path is not available') from exc


def _require_directory(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise FileTreeError(400, 'Path is not available') from exc
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise FileTreeError(400, 'Path is not available')


def _direct_children(directory: Path, root: Path, started: float) -> list[dict]:
    try:
        entries = list(directory.iterdir())
    except OSError as exc:
        raise FileTreeError(400, 'Path is not available') from exc
    if len(entries) > MAX_IMMEDIATE_ITEMS:
        raise FileTreeError(413, 'Directory exceeds listing limits')

    children: list[dict] = []
    for child in sorted(entries, key=lambda entry: entry.name):
        _check_time(started)
        try:
            mode = child.lstat().st_mode
        except OSError as exc:
            raise FileTreeError(400, 'Path is not available') from exc
        if stat.S_ISLNK(mode):
            continue
        if stat.S_ISDIR(mode):
            try:
                child.resolve(strict=True).relative_to(root)
            except (OSError, ValueError) as exc:
                raise FileTreeError(403, 'Path is not available') from exc
            child_type = 'directory'
        elif stat.S_ISREG(mode):
            child_type = 'file'
        else:
            continue
        children.append({
            'name': child.name,
            'path': str(CONTAINER_HOME / child.relative_to(root)),
            'type': child_type,
            'children': [],
        })
    return children


def _check_serialized_size(tree: dict) -> None:
    if len(json.dumps(tree, ensure_ascii=False, separators=(',', ':')).encode('utf-8')) > MAX_SERIALIZED_BYTES:
        raise FileTreeError(413, 'Directory exceeds listing limits')


def _check_time(started: float) -> None:
    if time.monotonic() - started > MAX_WALL_TIME_SECONDS:
        raise FileTreeError(422, 'Directory listing timed out')
