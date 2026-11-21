"""Tests for bin/install-claude.sh, the wrapper around the shared installer.

The installer itself (linking, the dangling-link report) is tested in its own
repository; these check only what ralpher passes it.
"""

import json
import os
import pathlib
import re
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[2]
WRAPPER = REPO / 'bin' / 'install-claude.sh'


def run_with_stub_uvx(tmp_path: pathlib.Path, *args: str) -> list[str]:
    """Run the wrapper with a uvx that records its arguments instead of running."""
    stub_dir = tmp_path / 'bin'
    stub_dir.mkdir()
    record = tmp_path / 'argv.json'
    stub = stub_dir / 'uvx'
    stub.write_text(f'#!/usr/bin/env python3\nimport json, sys\nopen({str(record)!r}, "w").write(json.dumps(sys.argv[1:]))\n')
    stub.chmod(0o755)
    env = {**os.environ, 'PATH': f'{stub_dir}{os.pathsep}{os.environ["PATH"]}'}
    subprocess.run([str(WRAPPER), *args], check=True, env=env)  # noqa: S603
    return json.loads(record.read_text())


def test_the_wrapper_passes_the_pinned_installer_and_ralphers_claude_files(tmp_path: pathlib.Path) -> None:
    argv = run_with_stub_uvx(tmp_path)
    assert argv[0] == '--from'
    assert re.fullmatch(r'git\+ssh://git@github\.com/bnomis/install-in-claude\.git@[0-9a-f]{40}', argv[1])
    assert argv[2:] == ['install-in-claude', '--source', str(REPO / 'claude')]


def test_extra_arguments_pass_through(tmp_path: pathlib.Path) -> None:
    argv = run_with_stub_uvx(tmp_path, '--dry-run', '--target', '/x')
    assert argv[-3:] == ['--dry-run', '--target', '/x']
