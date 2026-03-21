import pathlib

import git
import rich.text

import ralphlib.giter
import ralphlib.printer
import ralphlib.types


class TestDiscoverRepoPath:
    def test_returns_repo_for_valid_git_repo(self, tmp_path: pathlib.Path) -> None:
        git.Repo.init(str(tmp_path))
        result = ralphlib.giter.discover_repo_path(tmp_path)
        assert isinstance(result, git.Repo)

    def test_returns_none_for_non_git_directory(self, tmp_path: pathlib.Path) -> None:
        result = ralphlib.giter.discover_repo_path(tmp_path)
        assert result is None


class TestIsGitRepo:
    def test_returns_true_for_valid_git_repo(self, tmp_path: pathlib.Path) -> None:
        git.Repo.init(str(tmp_path))
        assert ralphlib.giter.is_git_repo(tmp_path) is True

    def test_returns_false_for_non_git_directory(self, tmp_path: pathlib.Path) -> None:
        assert ralphlib.giter.is_git_repo(tmp_path) is False


class TestIsWorkingTreeClean:
    def test_returns_true_for_clean_repo(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        # Create an initial commit so the repo has a HEAD
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(['README.md'])
        repo.index.commit('initial')
        assert ralphlib.giter.is_working_tree_clean(repo) is True

    def test_returns_false_for_modified_file(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(['README.md'])
        repo.index.commit('initial')
        readme.write_text('modified')
        assert ralphlib.giter.is_working_tree_clean(repo) is False

    def test_include_untracked_false_ignores_untracked(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(['README.md'])
        repo.index.commit('initial')
        (tmp_path / 'untracked.txt').write_text('new file')
        assert ralphlib.giter.is_working_tree_clean(repo, include_untracked=False) is True

    def test_include_untracked_true_detects_untracked(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(['README.md'])
        repo.index.commit('initial')
        (tmp_path / 'untracked.txt').write_text('new file')
        assert ralphlib.giter.is_working_tree_clean(repo, include_untracked=True) is False


class TestIsCleanStrict:
    def test_delegates_with_untracked(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(['README.md'])
        repo.index.commit('initial')
        # Clean repo should be clean strict
        assert ralphlib.giter.is_clean_strict(repo) is True
        # Untracked file makes it dirty
        (tmp_path / 'untracked.txt').write_text('new')
        assert ralphlib.giter.is_clean_strict(repo) is False


class TestIsCleanNoUntracked:
    def test_delegates_without_untracked(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(['README.md'])
        repo.index.commit('initial')
        # Untracked file should NOT make it dirty
        (tmp_path / 'untracked.txt').write_text('new')
        assert ralphlib.giter.is_clean_no_untracked(repo) is True
        # Modified tracked file should make it dirty
        readme.write_text('modified')
        assert ralphlib.giter.is_clean_no_untracked(repo) is False


class TestGetUpstreamBranch:
    def test_returns_none_for_detached_head(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(['README.md'])
        commit = repo.index.commit('initial')
        repo.head.reference = commit  # type: ignore[assignment]
        assert ralphlib.giter.get_upstream_branch(repo) is None

    def test_returns_none_when_no_tracking_branch(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(['README.md'])
        repo.index.commit('initial')
        # No remote set up, so no tracking branch
        assert ralphlib.giter.get_upstream_branch(repo) is None


class TestLinesToText:
    def test_returns_rich_text_with_joined_lines(self) -> None:
        lines = ['line one', 'line two', 'line three']
        result = ralphlib.giter.lines_to_text(lines)
        assert isinstance(result, rich.text.Text)
        assert result.plain == 'line one\nline two\nline three'
        expected_style = ralphlib.printer.type_to_style(ralphlib.types.MessageType.ALERT)
        assert str(result.style) == expected_style
