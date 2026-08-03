"""Focused shell runtime-limit coverage; all Docker calls are mocked."""
import subprocess
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

# ``routers.shell`` is POSIX-only at runtime, but these focused unit tests also
# collect on Windows.  Stub only the unavailable modules before its import.
if 'fcntl' not in sys.modules:
    fcntl = types.ModuleType('fcntl')
    fcntl.ioctl = lambda *_args: None
    sys.modules['fcntl'] = fcntl
if 'termios' not in sys.modules:
    termios = types.ModuleType('termios')
    termios.TIOCSWINSZ = 0
    sys.modules['termios'] = termios

from routers import shell


class _RunningProcess:
    def __init__(self):
        self.wait_timeouts = []
        self.terminated = False
        self.killed = False

    def poll(self):
        return None

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True

    def wait(self, timeout):
        self.wait_timeouts.append(timeout)
        if len(self.wait_timeouts) == 1:
            raise subprocess.TimeoutExpired('docker', timeout)


def test_start_uses_isolated_read_only_container(monkeypatch, tmp_path):
    session = shell.DockerSession('safe-name', 'admin')
    session.home_dir = tmp_path
    master_fd, slave_fd = __import__('os').pipe()
    commands = []

    monkeypatch.setattr(shell.os, 'openpty', lambda: (master_fd, slave_fd), raising=False)
    monkeypatch.setattr(shell.os, 'chown', lambda *_args: None, raising=False)
    monkeypatch.setattr(shell.os, 'setsid', lambda: None, raising=False)
    monkeypatch.setattr(shell.fcntl, 'ioctl', lambda *_args: None)
    monkeypatch.setattr(shell.subprocess, 'run', lambda command, **kwargs: commands.append((command, kwargs)))
    popen_calls = []

    def fake_popen(command, **kwargs):
        popen_calls.append((command, kwargs))
        return _RunningProcess()

    monkeypatch.setattr(shell.subprocess, 'Popen', fake_popen)
    monkeypatch.setattr(shell.time, 'sleep', lambda _seconds: None)

    session.start()
    session.cleanup()
    command, popen_kwargs = popen_calls[0]

    assert commands[0][0] == ['docker', 'rm', '-f', 'webterm-safe-name']
    assert commands[1][0] == ['docker', 'rm', '-f', 'webterm-safe-name']
    assert command[:5] == ['docker', 'run', '--rm', '-i', '--tty']
    for expected in (
        ('--network', 'none'), ('--cap-drop', 'ALL'),
        ('--security-opt', 'no-new-privileges'), ('--user', '1000:1000'),
    ):
        assert list(expected) == command[command.index(expected[0]):command.index(expected[0]) + 2]
    assert '--read-only' in command
    assert '/tmp:rw,noexec,nosuid,size=64m' in command
    assert '/run:rw,noexec,nosuid,size=16m' in command
    assert command[-3:] == ['webterm:latest', '/bin/bash', '--login']
    assert popen_kwargs['stdin'] == slave_fd
    session.cleanup()


def test_capacity_limits_are_checked_without_starting_docker(monkeypatch):
    monkeypatch.setattr(shell, 'ACTIVE_SESSIONS', {
        'one': SimpleNamespace(username='admin'),
    })
    assert shell._session_capacity_error('admin') == 'Shell session limit reached for this user'

    monkeypatch.setattr(shell, 'ACTIVE_SESSIONS', {
        str(index): SimpleNamespace(username=str(index)) for index in range(5)
    })
    assert shell._session_capacity_error('new-admin') == 'Shell service is at capacity'


def test_early_exit_removes_deterministic_orphan(monkeypatch, tmp_path):
    class _ExitedProcess:
        def poll(self):
            return 1

    session = shell.DockerSession('safe-name', 'admin')
    session.home_dir = tmp_path
    master_fd, slave_fd = __import__('os').pipe()
    commands = []
    monkeypatch.setattr(shell.os, 'openpty', lambda: (master_fd, slave_fd), raising=False)
    monkeypatch.setattr(shell.os, 'chown', lambda *_args: None, raising=False)
    monkeypatch.setattr(shell.os, 'setsid', lambda: None, raising=False)
    monkeypatch.setattr(shell.fcntl, 'ioctl', lambda *_args: None)
    monkeypatch.setattr(shell.subprocess, 'run', lambda command, **kwargs: commands.append((command, kwargs)))
    monkeypatch.setattr(shell.subprocess, 'Popen', lambda *_args, **_kwargs: _ExitedProcess())

    with pytest.raises(RuntimeError, match='exited during startup'):
        session.start()

    assert [command for command, _kwargs in commands] == [
        ['docker', 'rm', '-f', 'webterm-safe-name'],
        ['docker', 'rm', '-f', 'webterm-safe-name'],
    ]
    assert session.master_fd is None


def test_cleanup_has_bounded_idempotent_timeouts(monkeypatch):
    session = shell.DockerSession('safe-name', 'admin')
    process = _RunningProcess()
    session.proc = process
    calls = []
    monkeypatch.setattr(shell.subprocess, 'run', lambda command, **kwargs: calls.append((command, kwargs)))

    session.cleanup()
    session.cleanup()

    assert process.terminated and process.killed
    assert process.wait_timeouts == [2, 2]
    assert calls == [(['docker', 'rm', '-f', 'webterm-safe-name'], {
        'capture_output': True, 'timeout': 5, 'check': False,
    })]


def test_compose_socket_proxy_and_webterm_image_are_restricted():
    root = Path(__file__).resolve().parents[2]
    compose = (root / 'docker-compose.yml').read_text(encoding='utf-8')
    dockerfile = (root / 'Dockerfile.webterm').read_text(encoding='utf-8')

    assert 'DOCKER_HOST=tcp://docker-socket-proxy:2375' in compose
    assert 'docker-socket-proxy:' in compose
    assert compose.count('/var/run/docker.sock:/var/run/docker.sock:ro') == 1
    assert '- /var/run/docker.sock:/var/run/docker.sock\n' not in compose
    for permission in ('PING=1', 'VERSION=1', 'IMAGES=1', 'CONTAINERS=1', 'POST=1'):
        assert permission in compose
    assert 'USER user' in dockerfile
    assert 'docker' not in dockerfile.lower()
