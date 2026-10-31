import json
import pathlib
import unittest.mock

import git
import loguru
import pytest
import rich.text

import ralphlib.giter
import ralphlib.options
import ralphlib.printer
import ralphlib.settings
import ralphlib.types
import tests.helpers

README_FILES = ('README.md',)


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
        repo.index.add(list(README_FILES))
        repo.index.commit('initial')
        assert ralphlib.giter.is_working_tree_clean(repo) is True

    def test_returns_false_for_modified_file(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(list(README_FILES))
        repo.index.commit('initial')
        readme.write_text('modified')
        assert ralphlib.giter.is_working_tree_clean(repo) is False

    def test_include_untracked_false_ignores_untracked(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(list(README_FILES))
        repo.index.commit('initial')
        (tmp_path / 'untracked.txt').write_text('new file')
        assert ralphlib.giter.is_working_tree_clean(repo, include_untracked=False) is True

    def test_include_untracked_true_detects_untracked(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(list(README_FILES))
        repo.index.commit('initial')
        (tmp_path / 'untracked.txt').write_text('new file')
        assert ralphlib.giter.is_working_tree_clean(repo, include_untracked=True) is False


class TestIsCleanStrict:
    def test_delegates_with_untracked(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(list(README_FILES))
        repo.index.commit('initial')
        # Clean repo should be clean strict
        assert ralphlib.giter.is_working_tree_clean(repo, include_untracked=True) is True
        # Untracked file makes it dirty
        (tmp_path / 'untracked.txt').write_text('new')
        assert ralphlib.giter.is_working_tree_clean(repo, include_untracked=True) is False


class TestIsCleanNoUntracked:
    def test_delegates_without_untracked(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(list(README_FILES))
        repo.index.commit('initial')
        # Untracked file should NOT make it dirty
        (tmp_path / 'untracked.txt').write_text('new')
        assert ralphlib.giter.is_working_tree_clean(repo, include_untracked=False) is True
        # Modified tracked file should make it dirty
        readme.write_text('modified')
        assert ralphlib.giter.is_working_tree_clean(repo, include_untracked=False) is False


class TestGetUpstreamBranch:
    def test_returns_none_for_detached_head(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(list(README_FILES))
        commit = repo.index.commit('initial')
        repo.head.reference = commit  # type: ignore[assignment]
        assert ralphlib.giter.get_upstream_branch(repo) is None

    def test_returns_none_when_no_tracking_branch(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(list(README_FILES))
        repo.index.commit('initial')
        # No remote set up, so no tracking branch
        assert ralphlib.giter.get_upstream_branch(repo) is None


class TestLinesToText:
    def test_returns_rich_text_with_joined_lines(self) -> None:
        options = tests.helpers.make_options()
        lines = ['line one', 'line two', 'line three']
        result = ralphlib.giter.lines_to_text(options, lines)
        assert isinstance(result, rich.text.Text)
        assert result.plain == 'line one\nline two\nline three'
        expected_style = ralphlib.printer.type_to_style(options, ralphlib.types.MessageType.ALERT)
        assert str(result.style) == expected_style


def write_settings(path: pathlib.Path, settings: object) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings))
    return path


class TestClaudeSettingsPaths:
    def test_lowest_precedence_first(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(pathlib.Path, 'home', lambda: tmp_path / 'home')
        monkeypatch.setattr(ralphlib.giter.sys, 'platform', 'linux')
        repo = git.Repo.init(str(tmp_path / 'repo'))
        paths = ralphlib.giter.claude_settings_paths(repo)
        assert paths[:4] == [
            tmp_path / 'home' / '.claude' / 'settings.json',
            tmp_path / 'repo' / '.claude' / 'settings.json',
            tmp_path / 'repo' / '.claude' / 'settings.local.json',
            pathlib.Path('/etc/claude-code/managed-settings.json'),
        ]


class TestClaudeWorktreeBaseRef:
    @pytest.fixture
    def repo(self, tmp_path: pathlib.Path) -> git.Repo:
        return git.Repo.init(str(tmp_path))

    def use_settings(self, monkeypatch: pytest.MonkeyPatch, paths: list[pathlib.Path]) -> None:
        monkeypatch.setattr(ralphlib.giter, 'claude_settings_paths', lambda repo: paths)

    def test_defaults_to_fresh_without_settings(self, repo: git.Repo, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.use_settings(monkeypatch, [tmp_path / 'missing.json'])
        assert ralphlib.giter.claude_worktree_base_ref(repo) == 'fresh'

    def test_reads_base_ref(self, repo: git.Repo, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        user = write_settings(tmp_path / 'user.json', {'worktree': {'baseRef': 'head'}})
        self.use_settings(monkeypatch, [user])
        assert ralphlib.giter.claude_worktree_base_ref(repo) == 'head'

    def test_higher_precedence_wins(self, repo: git.Repo, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        user = write_settings(tmp_path / 'user.json', {'worktree': {'baseRef': 'head'}})
        local = write_settings(tmp_path / 'local.json', {'worktree': {'baseRef': 'fresh'}})
        self.use_settings(monkeypatch, [user, local])
        assert ralphlib.giter.claude_worktree_base_ref(repo) == 'fresh'

    def test_file_without_key_keeps_lower_value(self, repo: git.Repo, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        user = write_settings(tmp_path / 'user.json', {'worktree': {'baseRef': 'head'}})
        project = write_settings(tmp_path / 'project.json', {'worktree': {'symlinkDirectories': ['node_modules']}})
        self.use_settings(monkeypatch, [user, project])
        assert ralphlib.giter.claude_worktree_base_ref(repo) == 'head'

    def test_ignores_invalid_json(self, repo: git.Repo, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        user = write_settings(tmp_path / 'user.json', {'worktree': {'baseRef': 'head'}})
        broken = tmp_path / 'broken.json'
        broken.write_text('{not json')
        self.use_settings(monkeypatch, [user, broken])
        assert ralphlib.giter.claude_worktree_base_ref(repo) == 'head'


class TestCheckDivergence:
    def test_skipped_when_base_ref_is_head(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ralphlib.giter, 'claude_worktree_base_ref', lambda repo: 'head')
        monkeypatch.setattr(ralphlib.giter, 'get_origin', lambda repo: pytest.fail('origin checked'))
        ralphlib.giter.check_divergence(tests.helpers.make_options(), git.Repo.init(str(tmp_path)))

    def test_checks_origin_when_base_ref_is_fresh(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ralphlib.giter, 'claude_worktree_base_ref', lambda repo: 'fresh')
        monkeypatch.setattr(ralphlib.giter, 'get_origin', lambda repo: ('origin/main', 'main'))
        monkeypatch.setattr(ralphlib.giter, 'get_current_branch', lambda repo: 'feature')
        monkeypatch.setattr(ralphlib.giter.YNConfirm, 'ask', lambda *args, **kwargs: True)
        with pytest.raises(SystemExit):
            ralphlib.giter.check_divergence(tests.helpers.make_options(), git.Repo.init(str(tmp_path)))


class TestCheckRepoClean:
    @pytest.fixture
    def dirty_repo(self, tmp_path: pathlib.Path) -> git.Repo:
        repo = git.Repo.init(str(tmp_path))
        (tmp_path / 'untracked.txt').write_text('x')
        return repo

    def capture_prompts(self, monkeypatch: pytest.MonkeyPatch) -> list[str]:
        prompts: list[str] = []
        monkeypatch.setattr(ralphlib.giter.YNConfirm, 'ask', lambda prompt, **kwargs: prompts.append(prompt.plain) or True)
        return prompts

    def test_head_base_ref_skips_unpushed_check(self, dirty_repo: git.Repo, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ralphlib.giter, 'claude_worktree_base_ref', lambda repo: 'head')
        monkeypatch.setattr(ralphlib.giter, 'has_unpushed_commits', lambda repo: pytest.fail('unpushed checked'))
        prompts = self.capture_prompts(monkeypatch)
        ralphlib.giter.check_repo_clean(tests.helpers.make_options(worktree=True), dirty_repo)
        assert len(prompts) == 1
        assert 'local HEAD' in prompts[0]

    def test_fresh_base_ref_checks_unpushed(self, dirty_repo: git.Repo, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ralphlib.giter, 'claude_worktree_base_ref', lambda repo: 'fresh')
        monkeypatch.setattr(ralphlib.giter, 'has_unpushed_commits', lambda repo: True)
        prompts = self.capture_prompts(monkeypatch)
        ralphlib.giter.check_repo_clean(tests.helpers.make_options(worktree=True), dirty_repo)
        assert len(prompts) == 2
        assert all('origin repo' in prompt for prompt in prompts)

    def test_without_worktree_checks_unpushed(self, dirty_repo: git.Repo, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ralphlib.giter, 'claude_worktree_base_ref', lambda repo: 'head')
        monkeypatch.setattr(ralphlib.giter, 'has_unpushed_commits', lambda repo: True)
        prompts = self.capture_prompts(monkeypatch)
        ralphlib.giter.check_repo_clean(tests.helpers.make_options(worktree=False), dirty_repo)
        assert len(prompts) == 2
        assert not any('worktree' in prompt for prompt in prompts)


class TestHasUnpushedCommitsFetch:
    def make_repo(self, error: Exception) -> unittest.mock.MagicMock:
        repo = unittest.mock.MagicMock()
        repo.remotes.origin.fetch.side_effect = error
        return repo

    def test_fetch_git_error_warns_and_returns_false(self) -> None:
        repo = self.make_repo(git.GitCommandError('fetch', 1))
        messages: list[str] = []
        sink_id = loguru.logger.add(messages.append, level='WARNING')
        try:
            assert ralphlib.giter.has_unpushed_commits(repo) is False
        finally:
            loguru.logger.remove(sink_id)
        assert any('Fetch failed' in message for message in messages)

    def test_fetch_other_error_propagates(self) -> None:
        repo = self.make_repo(RuntimeError('boom'))
        with pytest.raises(RuntimeError):
            ralphlib.giter.has_unpushed_commits(repo)
