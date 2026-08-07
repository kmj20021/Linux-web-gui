import asyncio
import sys
import types
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI, HTTPException

from services.file_tree import FileTreeError, build_lazy_tree

# The service is platform-neutral; only importing the shell router needs these
# POSIX-only modules on the Windows test host.
if sys.platform == 'win32':
    sys.modules.setdefault('fcntl', types.SimpleNamespace(ioctl=lambda *args: None))
    sys.modules.setdefault('termios', types.SimpleNamespace(TIOCSWINSZ=0))
from routers import shell


def _assert_rejected(root: Path, path: str, expected_status: int) -> None:
    with pytest.raises(FileTreeError) as error:
        build_lazy_tree(root, path)
    assert error.value.status_code == expected_status
    assert str(root) not in error.value.detail


def test_rejects_non_absolute_parent_and_outside_paths(tmp_path: Path) -> None:
    _assert_rejected(tmp_path, 'relative', 400)
    _assert_rejected(tmp_path, '/home/user/../outside', 400)
    _assert_rejected(tmp_path, '/tmp/outside', 403)


def test_rejects_file_path_and_depth_over_limit(tmp_path: Path) -> None:
    (tmp_path / 'plain-file').write_text('x')
    _assert_rejected(tmp_path, '/home/user/plain-file', 400)
    current = tmp_path
    for index in range(16):
        current = current / f'nested-{index}'
        current.mkdir()
    accepted = '/home/user/' + '/'.join(f'nested-{index}' for index in range(16))
    assert build_lazy_tree(tmp_path, accepted)['path'] == accepted
    deep = '/home/user/' + '/'.join(['nested'] * 17)
    _assert_rejected(tmp_path, deep, 422)


def test_lazy_listing_is_one_level_sorted_and_has_no_host_metadata(tmp_path: Path) -> None:
    (tmp_path / 'z-file').write_text('z')
    directory = tmp_path / 'a-directory'
    directory.mkdir()
    (directory / 'hidden-child').write_text('not listed')

    tree = build_lazy_tree(tmp_path)

    assert tree == {
        'name': 'user',
        'path': '/home/user',
        'type': 'directory',
        'children': [
            {'name': 'a-directory', 'path': '/home/user/a-directory', 'type': 'directory', 'children': []},
            {'name': 'z-file', 'path': '/home/user/z-file', 'type': 'file', 'children': []},
        ],
    }
    rendered = repr(tree)
    for prohibited in (str(tmp_path), 'mtime', 'mode', 'permission', 'hidden-child'):
        assert prohibited not in rendered


def test_rejects_large_directories_without_partial_result(tmp_path: Path) -> None:
    for index in range(201):
        (tmp_path / f'file-{index}').write_text('x')
    _assert_rejected(tmp_path, '/home/user', 413)


def test_symlinks_are_excluded_and_symlink_targets_are_rejected(tmp_path: Path) -> None:
    target = tmp_path / 'target'
    target.mkdir()
    (target / 'inside').write_text('x')
    link = tmp_path / 'link'
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip('symlink creation is unavailable on this platform')

    assert build_lazy_tree(tmp_path)['children'] == [
        {'name': 'target', 'path': '/home/user/target', 'type': 'directory', 'children': []},
    ]
    _assert_rejected(tmp_path, '/home/user/link', 400)


def test_circular_symlink_is_excluded(tmp_path: Path) -> None:
    loop = tmp_path / 'loop'
    try:
        loop.symlink_to(loop)
    except (OSError, NotImplementedError):
        pytest.skip('symlink creation is unavailable on this platform')
    assert build_lazy_tree(tmp_path)['children'] == []


def _request(app: FastAPI, url: str) -> httpx.Response:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
            return await client.get(url)

    return asyncio.run(send_request())


def test_route_requires_auth_and_preserves_session_semantics(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(shell, 'WEBTERM_HOME', tmp_path)
    monkeypatch.setattr(shell, 'ACTIVE_SESSIONS', {})
    monkeypatch.setattr(shell, 'USER_LATEST_SESSION', {})
    (tmp_path / 'owner').mkdir()
    (tmp_path / 'owner' / 'visible').write_text('x')
    session = shell.DockerSession('known', 'owner')
    shell.ACTIVE_SESSIONS['known'] = session
    app = FastAPI()
    app.include_router(shell.router)

    async def unauthorized_user():
        raise HTTPException(status_code=401, detail='Could not validate credentials')

    app.dependency_overrides[shell.get_current_user] = unauthorized_user
    assert _request(app, '/api/shell/fs?session_id=known').status_code == 401

    async def owner_viewer():
        return types.SimpleNamespace(username='owner', role='viewer', is_active=True)

    app.dependency_overrides[shell.get_current_user] = owner_viewer
    assert _request(app, '/api/shell/fs?session_id=missing').status_code == 404

    async def other_viewer():
        return types.SimpleNamespace(username='other', role='viewer', is_active=True)

    app.dependency_overrides[shell.get_current_user] = other_viewer
    assert _request(app, '/api/shell/fs?session_id=known').status_code == 403

    app.dependency_overrides[shell.get_current_user] = owner_viewer
    response = _request(app, '/api/shell/fs?session_id=known')
    assert response.status_code == 200
    assert response.json()['tree']['children'] == [
        {'name': 'visible', 'path': '/home/user/visible', 'type': 'file', 'children': []},
    ]
