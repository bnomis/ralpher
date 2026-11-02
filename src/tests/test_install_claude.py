import argparse
import importlib.util
import pathlib
import types

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[2] / 'bin' / 'install-claude.py'
OPTIONS = argparse.Namespace()


@pytest.fixture
def install_claude() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location('install_claude', SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestSymlinkFile:
    def test_links_a_new_file(self, install_claude: types.ModuleType, tmp_path: pathlib.Path) -> None:
        src = tmp_path / 'src' / 'a.md'
        src.parent.mkdir()
        src.write_text('x')
        dst = tmp_path / 'dst' / 'a.md'
        dst.parent.mkdir()
        install_claude.symlink_file(OPTIONS, src, dst)
        assert dst.is_symlink()
        assert dst.resolve() == src.resolve()

    def test_replaces_an_existing_symlink(self, install_claude: types.ModuleType, tmp_path: pathlib.Path) -> None:
        src = tmp_path / 'a.md'
        src.write_text('x')
        old = tmp_path / 'old.md'
        old.write_text('old')
        dst = tmp_path / 'link.md'
        dst.symlink_to(old)
        install_claude.symlink_file(OPTIONS, src, dst)
        assert dst.resolve() == src.resolve()
        assert old.read_text() == 'old'

    def test_renames_an_existing_regular_file(self, install_claude: types.ModuleType, tmp_path: pathlib.Path) -> None:
        src = tmp_path / 'src.md'
        src.write_text('new')
        dst = tmp_path / 'dst.md'
        dst.write_text('mine')
        install_claude.symlink_file(OPTIONS, src, dst)
        assert dst.is_symlink()
        assert (tmp_path / 'dst.md.orig').read_text() == 'mine'


class TestFindDanglingSymlinks:
    def test_reports_a_dangling_link(self, install_claude: types.ModuleType, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
        (tmp_path / 'gone.md').symlink_to(tmp_path / 'missing.md')
        install_claude.report_dangling_symlinks(OPTIONS, tmp_path)
        out = capsys.readouterr().out
        assert 'Dangling symlinks found' in out
        assert str(tmp_path / 'gone.md') in out

    def test_silent_when_every_link_resolves(self, install_claude: types.ModuleType, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
        (tmp_path / 'real.md').write_text('x')
        (tmp_path / 'ok.md').symlink_to(tmp_path / 'real.md')
        install_claude.report_dangling_symlinks(OPTIONS, tmp_path)
        assert capsys.readouterr().out == ''

    def test_does_not_descend_past_max_depth(self, install_claude: types.ModuleType, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
        deep = tmp_path / 'a' / 'b'
        deep.mkdir(parents=True)
        (deep / 'gone.md').symlink_to(tmp_path / 'missing.md')
        install_claude.report_dangling_symlinks(OPTIONS, tmp_path, max_depth=2)
        assert capsys.readouterr().out == ''
