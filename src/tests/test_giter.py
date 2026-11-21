import json
import pathlib
import tempfile
import unittest.mock

import git
import hypothesis
import hypothesis.strategies
import loguru
import pytest
import rich.text

import ralphlib.exceptions
import ralphlib.giter
import ralphlib.options
import ralphlib.printer
import ralphlib.settings
import ralphlib.types
import tests.helpers

README_FILES = ('README.md',)
# auditme: accept[non-alphabetical-literal] (base ref, short name): the order is the meaning
ORIGIN_MAIN = ('origin/main', 'main')


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
        assert ralphlib.giter.opens_as_repo(tmp_path) is True

    def test_returns_false_for_non_git_directory(self, tmp_path: pathlib.Path) -> None:
        assert ralphlib.giter.opens_as_repo(tmp_path) is False


class TestIsWorkingTreeClean:
    def test_returns_true_for_clean_repo(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(list(README_FILES))
        repo.index.commit('initial')
        assert ralphlib.giter.working_tree_is_clean(repo) is True

    def test_returns_false_for_modified_file(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(list(README_FILES))
        repo.index.commit('initial')
        readme.write_text('modified')
        assert ralphlib.giter.working_tree_is_clean(repo) is False

    def test_include_untracked_false_ignores_untracked(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(list(README_FILES))
        repo.index.commit('initial')
        (tmp_path / 'untracked.txt').write_text('new file')
        assert ralphlib.giter.working_tree_is_clean(repo, include_untracked=False) is True

    def test_include_untracked_true_detects_untracked(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(list(README_FILES))
        repo.index.commit('initial')
        (tmp_path / 'untracked.txt').write_text('new file')
        assert ralphlib.giter.working_tree_is_clean(repo, include_untracked=True) is False


class TestIsCleanStrict:
    def test_delegates_with_untracked(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(list(README_FILES))
        repo.index.commit('initial')
        assert ralphlib.giter.working_tree_is_clean(repo, include_untracked=True) is True
        (tmp_path / 'untracked.txt').write_text('new')
        assert ralphlib.giter.working_tree_is_clean(repo, include_untracked=True) is False


class TestIsCleanNoUntracked:
    def test_delegates_without_untracked(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(list(README_FILES))
        repo.index.commit('initial')
        (tmp_path / 'untracked.txt').write_text('new')
        assert ralphlib.giter.working_tree_is_clean(repo, include_untracked=False) is True
        readme.write_text('modified')
        assert ralphlib.giter.working_tree_is_clean(repo, include_untracked=False) is False


class TestGetUpstreamBranch:
    def test_returns_none_for_detached_head(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(list(README_FILES))
        commit = repo.index.commit('initial')
        repo.head.reference = commit  # type: ignore[assignment]
        assert ralphlib.giter.read_upstream_branch(repo) is None

    def test_returns_none_when_no_tracking_branch(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        readme = tmp_path / 'README.md'
        readme.write_text('hello')
        repo.index.add(list(README_FILES))
        repo.index.commit('initial')
        assert ralphlib.giter.read_upstream_branch(repo) is None


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


class TestWorktreeBaseRef:
    def test_option_overrides_settings(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ralphlib.giter, 'claude_worktree_base_ref', lambda repo: 'head')
        options = tests.helpers.make_options(worktree_base_ref='fresh')
        assert ralphlib.giter.worktree_base_ref(options, git.Repo.init(str(tmp_path))) == 'fresh'

    def test_settings_used_without_option(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ralphlib.giter, 'claude_worktree_base_ref', lambda repo: 'head')
        options = tests.helpers.make_options()
        assert ralphlib.giter.worktree_base_ref(options, git.Repo.init(str(tmp_path))) == 'head'


class TestCheckDivergence:
    def diverge(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """origin/HEAD points at main while a feature branch is checked out, and the prompt answers yes."""
        monkeypatch.setattr(ralphlib.giter, 'read_origin', lambda repo: ORIGIN_MAIN)
        monkeypatch.setattr(ralphlib.giter, 'read_current_branch', lambda repo: 'feature')
        monkeypatch.setattr(ralphlib.giter.YNConfirm, 'ask', lambda *args, **kwargs: True)

    def test_skipped_when_base_ref_is_head(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ralphlib.giter, 'claude_worktree_base_ref', lambda repo: 'head')
        monkeypatch.setattr(ralphlib.giter, 'read_origin', lambda repo: pytest.fail('origin checked'))
        ralphlib.giter.confirm_divergence(tests.helpers.make_options(), git.Repo.init(str(tmp_path)))

    def test_checks_origin_when_base_ref_is_fresh(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ralphlib.giter, 'claude_worktree_base_ref', lambda repo: 'fresh')
        self.diverge(monkeypatch)
        with pytest.raises(SystemExit):
            ralphlib.giter.confirm_divergence(tests.helpers.make_options(), git.Repo.init(str(tmp_path)))

    def test_option_fresh_checks_origin_despite_head_setting(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ralphlib.giter, 'claude_worktree_base_ref', lambda repo: 'head')
        self.diverge(monkeypatch)
        with pytest.raises(SystemExit):
            ralphlib.giter.confirm_divergence(tests.helpers.make_options(worktree_base_ref='fresh'), git.Repo.init(str(tmp_path)))

    def test_option_head_skips_origin_despite_fresh_setting(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ralphlib.giter, 'claude_worktree_base_ref', lambda repo: 'fresh')
        monkeypatch.setattr(ralphlib.giter, 'read_origin', lambda repo: pytest.fail('origin checked'))
        ralphlib.giter.confirm_divergence(tests.helpers.make_options(worktree_base_ref='head'), git.Repo.init(str(tmp_path)))


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
        monkeypatch.setattr(ralphlib.giter, 'fetch_unpushed_state', lambda repo: pytest.fail('unpushed checked'))
        prompts = self.capture_prompts(monkeypatch)
        ralphlib.giter.confirm_repo_clean(tests.helpers.make_options(worktree=True), dirty_repo)
        assert len(prompts) == 1
        assert 'local HEAD' in prompts[0]

    def test_fresh_base_ref_checks_unpushed(self, dirty_repo: git.Repo, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ralphlib.giter, 'claude_worktree_base_ref', lambda repo: 'fresh')
        monkeypatch.setattr(ralphlib.giter, 'fetch_unpushed_state', lambda repo: True)
        prompts = self.capture_prompts(monkeypatch)
        ralphlib.giter.confirm_repo_clean(tests.helpers.make_options(worktree=True), dirty_repo)
        assert len(prompts) == 2
        assert all('origin repo' in prompt for prompt in prompts)

    def test_without_worktree_checks_unpushed(self, dirty_repo: git.Repo, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ralphlib.giter, 'claude_worktree_base_ref', lambda repo: 'head')
        monkeypatch.setattr(ralphlib.giter, 'fetch_unpushed_state', lambda repo: True)
        prompts = self.capture_prompts(monkeypatch)
        ralphlib.giter.confirm_repo_clean(tests.helpers.make_options(worktree=False), dirty_repo)
        assert len(prompts) == 2
        assert not any('worktree' in prompt for prompt in prompts)

    def test_option_fresh_checks_unpushed_despite_head_setting(self, dirty_repo: git.Repo, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ralphlib.giter, 'claude_worktree_base_ref', lambda repo: 'head')
        monkeypatch.setattr(ralphlib.giter, 'fetch_unpushed_state', lambda repo: True)
        prompts = self.capture_prompts(monkeypatch)
        ralphlib.giter.confirm_repo_clean(tests.helpers.make_options(worktree=True, worktree_base_ref='fresh'), dirty_repo)
        assert len(prompts) == 2
        assert all('origin repo' in prompt for prompt in prompts)

    def test_cannot_tell_warns_and_asks(self, dirty_repo: git.Repo, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ralphlib.giter, 'claude_worktree_base_ref', lambda repo: 'fresh')
        monkeypatch.setattr(ralphlib.giter, 'fetch_unpushed_state', lambda repo: None)
        prompts = self.capture_prompts(monkeypatch)
        ralphlib.giter.confirm_repo_clean(tests.helpers.make_options(worktree=True), dirty_repo)
        assert len(prompts) == 2
        assert 'cannot tell' in prompts[1]

    def test_no_unpushed_commits_does_not_ask(self, dirty_repo: git.Repo, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ralphlib.giter, 'claude_worktree_base_ref', lambda repo: 'fresh')
        monkeypatch.setattr(ralphlib.giter, 'fetch_unpushed_state', lambda repo: False)
        prompts = self.capture_prompts(monkeypatch)
        ralphlib.giter.confirm_repo_clean(tests.helpers.make_options(worktree=True), dirty_repo)
        assert len(prompts) == 1


class TestRedactUrl:
    @pytest.mark.parametrize(
        ('url', 'expected'),
        [
            ('/local/path/repo', '/local/path/repo'),
            ('git@github.com:org/repo.git', 'git@github.com:org/repo.git'),
            ('https://example.com/a.git', 'https://example.com/a.git'),
            ('https://token@example.com/a.git', 'https://example.com/a.git'),
            ('https://user:pw@example.com/a.git', 'https://example.com/a.git'),
        ],
    )
    def test_redact_url(self, url: str, expected: str) -> None:
        assert ralphlib.giter.redact_url(url) == expected


class TestHasUnpushedCommitsFetch:
    def make_repo(self, error: Exception) -> unittest.mock.MagicMock:
        repo = unittest.mock.MagicMock()
        repo.remotes.origin.fetch.side_effect = error
        repo.remotes.origin.url = 'https://example.com/org/repo.git'
        return repo

    def test_fetch_git_error_warns_and_returns_none(self) -> None:
        repo = self.make_repo(git.GitCommandError('fetch', 1))
        messages: list[str] = []
        sink_id = loguru.logger.add(messages.append, level='WARNING')
        try:
            assert ralphlib.giter.fetch_unpushed_state(repo) is None
        finally:
            loguru.logger.remove(sink_id)
        assert any('Fetch failed' in message for message in messages)

    def test_fetch_warning_omits_url_credentials(self) -> None:
        repo = self.make_repo(git.GitCommandError('fetch', 1))
        repo.remotes.origin.url = 'https://user:token123@example.com/org/repo.git'
        repo.remotes.origin.fetch.side_effect = git.GitCommandError('fetch', 1, stderr='fatal: unable to access https://user:token123@example.com/org/repo.git')
        messages: list[str] = []
        sink_id = loguru.logger.add(messages.append, level='WARNING')
        try:
            ralphlib.giter.fetch_unpushed_state(repo)
        finally:
            loguru.logger.remove(sink_id)
        assert messages
        assert not any('token123' in message for message in messages)
        assert any('example.com/org/repo.git' in message for message in messages)

    def test_fetch_other_error_propagates(self) -> None:
        repo = self.make_repo(RuntimeError('boom'))
        with pytest.raises(RuntimeError):
            ralphlib.giter.fetch_unpushed_state(repo)


class TestDomainErrors:
    def test_discover_repo_path_translates_os_error(self, tmp_path: pathlib.Path) -> None:
        with unittest.mock.patch('git.Repo', side_effect=OSError('denied')), pytest.raises(ralphlib.exceptions.GitError):
            ralphlib.giter.discover_repo_path(tmp_path)

    def test_working_tree_is_clean_translates_command_error(self) -> None:
        repo = unittest.mock.MagicMock()
        repo.is_dirty.side_effect = git.GitCommandError('status', 1)
        with pytest.raises(ralphlib.exceptions.GitError):
            ralphlib.giter.working_tree_is_clean(repo)

    def test_read_upstream_branch_translates_os_error(self) -> None:
        repo = unittest.mock.MagicMock()
        type(repo.head).is_detached = unittest.mock.PropertyMock(side_effect=OSError('denied'))
        with pytest.raises(ralphlib.exceptions.GitError):
            ralphlib.giter.read_upstream_branch(repo)

    def test_read_current_branch_translates_os_error(self) -> None:
        repo = unittest.mock.MagicMock()
        type(repo.head).is_detached = unittest.mock.PropertyMock(side_effect=OSError('denied'))
        with pytest.raises(ralphlib.exceptions.GitError):
            ralphlib.giter.read_current_branch(repo)

    def test_fetch_unpushed_state_translates_iter_commits_error(self) -> None:
        repo = unittest.mock.MagicMock()
        repo.head.is_detached = False
        repo.iter_commits.side_effect = git.GitCommandError('rev-list', 1)
        with pytest.raises(ralphlib.exceptions.GitError):
            ralphlib.giter.fetch_unpushed_state(repo)

    def test_discover_repo_path_translates_missing_cwd(self) -> None:
        with unittest.mock.patch('pathlib.Path.cwd', side_effect=FileNotFoundError('gone')), pytest.raises(ralphlib.exceptions.GitError):
            ralphlib.giter.discover_repo_path()

    def test_working_tree_is_clean_translates_command_not_found(self) -> None:
        repo = unittest.mock.MagicMock()
        repo.is_dirty.side_effect = git.GitCommandNotFound('git', 'missing')
        with pytest.raises(ralphlib.exceptions.GitError):
            ralphlib.giter.working_tree_is_clean(repo)

    def test_fetch_unpushed_state_reports_fetch_command_not_found(self) -> None:
        repo = unittest.mock.MagicMock()
        repo.remotes.origin.url = 'https://example.com/org/repo.git'
        repo.remotes.origin.fetch.side_effect = git.GitCommandNotFound('git', 'missing')
        assert ralphlib.giter.fetch_unpushed_state(repo) is None

    def test_fetch_unpushed_state_translates_iter_commits_command_not_found(self) -> None:
        repo = unittest.mock.MagicMock()
        repo.head.is_detached = False
        repo.iter_commits.side_effect = git.GitCommandNotFound('git', 'missing')
        with pytest.raises(ralphlib.exceptions.GitError):
            ralphlib.giter.fetch_unpushed_state(repo)

    def test_fetch_unpushed_state_without_origin_returns_none(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        assert ralphlib.giter.fetch_unpushed_state(repo) is None

    def test_fetch_unpushed_state_reports_fetch_os_error(self) -> None:
        repo = unittest.mock.MagicMock()
        repo.remotes.origin.url = 'https://example.com/org/repo.git'
        repo.remotes.origin.fetch.side_effect = OSError('no FETCH_HEAD')
        assert ralphlib.giter.fetch_unpushed_state(repo) is None


class TestYNConfirmMakePrompt:
    def test_default_yes_capitalises_y(self) -> None:
        assert ralphlib.giter.YNConfirm('Exit now?').make_prompt(True).plain == 'Exit now? [Y/n] '

    def test_default_no_capitalises_n(self) -> None:
        assert ralphlib.giter.YNConfirm('Exit now?').make_prompt(False).plain == 'Exit now? [y/N] '


class TestGetOrigin:
    def test_no_origin_head_gives_none(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        repo.create_remote('origin', 'https://example.invalid/probe.git')
        assert ralphlib.giter.read_origin(repo) == (None, None)

    def test_origin_head_gives_base_and_short_name(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        (tmp_path / 'README.md').write_text('hello')
        repo.index.add(list(README_FILES))
        commit = repo.index.commit('initial')
        repo.create_remote('origin', 'https://example.invalid/probe.git')
        git.Reference.create(repo, 'refs/remotes/origin/main', commit.hexsha)
        repo.git.symbolic_ref('refs/remotes/origin/HEAD', 'refs/remotes/origin/main')
        assert ralphlib.giter.read_origin(repo) == ORIGIN_MAIN


class TestGetCurrentBranch:
    def test_detached_head_gives_none(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        (tmp_path / 'README.md').write_text('hello')
        repo.index.add(list(README_FILES))
        repo.head.reference = repo.index.commit('initial')  # type: ignore[assignment]
        assert ralphlib.giter.read_current_branch(repo) is None


class TestLastCommitSummary:
    def test_returns_summary_of_last_commit(self, tmp_path: pathlib.Path) -> None:
        repo = git.Repo.init(str(tmp_path))
        (tmp_path / 'README.md').write_text('hello')
        repo.index.add(list(README_FILES))
        repo.index.commit('initial')
        assert ralphlib.giter.last_commit_summary(tmp_path) == 'initial'

    def test_returns_empty_string_without_commits(self, tmp_path: pathlib.Path) -> None:
        git.Repo.init(str(tmp_path))
        assert ralphlib.giter.last_commit_summary(tmp_path) == ''

    def test_keyboard_interrupt_propagates(self, tmp_path: pathlib.Path) -> None:
        git.Repo.init(str(tmp_path))
        with (
            unittest.mock.patch.object(git.Repo, 'head', new_callable=unittest.mock.PropertyMock, side_effect=KeyboardInterrupt),
            pytest.raises(KeyboardInterrupt),
        ):
            ralphlib.giter.last_commit_summary(tmp_path)

    def test_os_error_raises_git_error(self, tmp_path: pathlib.Path) -> None:
        git.Repo.init(str(tmp_path))
        with (
            unittest.mock.patch.object(git.Repo, 'head', new_callable=unittest.mock.PropertyMock, side_effect=OSError('denied')),
            pytest.raises(ralphlib.exceptions.GitError),
        ):
            ralphlib.giter.last_commit_summary(tmp_path)


class TestConfirmGitState:
    @pytest.fixture
    def clean_repo(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
        repo = git.Repo.init(str(tmp_path))
        (tmp_path / 'README.md').write_text('hello')
        repo.index.add(list(README_FILES))
        repo.index.commit('initial')
        monkeypatch.setattr(ralphlib.giter, 'claude_worktree_base_ref', lambda repo: 'fresh')
        monkeypatch.setattr(ralphlib.giter, 'fetch_unpushed_state', lambda repo: False)
        return tmp_path

    def answer(self, monkeypatch: pytest.MonkeyPatch, decision: bool) -> list[str]:
        prompts: list[str] = []
        monkeypatch.setattr(ralphlib.giter.YNConfirm, 'ask', lambda prompt, **kwargs: prompts.append(prompt.plain) or decision)
        return prompts

    def test_skip_git_check_asks_nothing(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        prompts = self.answer(monkeypatch, False)
        ralphlib.giter.confirm_git_state(tests.helpers.make_options(skip_git_check=True), tmp_path)
        assert prompts == []

    def test_not_a_repository_aborts_when_declined(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        prompts = self.answer(monkeypatch, False)
        with pytest.raises(SystemExit, match='not being in a git repository'):
            ralphlib.giter.confirm_git_state(tests.helpers.make_options(), tmp_path)
        assert 'not in a git repository' in prompts[0]

    def test_not_a_repository_continues_when_accepted(self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.answer(monkeypatch, True)
        ralphlib.giter.confirm_git_state(tests.helpers.make_options(), tmp_path)

    def test_clean_repository_asks_nothing(self, clean_repo: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        prompts = self.answer(monkeypatch, False)
        ralphlib.giter.confirm_git_state(tests.helpers.make_options(), clean_repo)
        assert prompts == []

    def test_dirty_tree_aborts_when_declined(self, clean_repo: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        (clean_repo / 'untracked.txt').write_text('x')
        prompts = self.answer(monkeypatch, False)
        with pytest.raises(SystemExit, match='unclean git working tree'):
            ralphlib.giter.confirm_git_state(tests.helpers.make_options(), clean_repo)
        assert 'not clean' in prompts[0]

    def test_divergence_aborts_only_with_a_worktree(self, clean_repo: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ralphlib.giter, 'read_origin', lambda repo: ORIGIN_MAIN)
        monkeypatch.setattr(ralphlib.giter, 'read_current_branch', lambda repo: 'feature')
        prompts = self.answer(monkeypatch, True)
        ralphlib.giter.confirm_git_state(tests.helpers.make_options(), clean_repo)
        assert prompts == []
        with pytest.raises(SystemExit, match='divergence'):
            ralphlib.giter.confirm_git_state(tests.helpers.make_options(worktree=True), clean_repo)
        assert 'will diverge' in prompts[0]


SCHEMES = hypothesis.strategies.from_regex(r'[a-z][a-z0-9+.-]{0,8}://', fullmatch=True)
HOSTS = hypothesis.strategies.from_regex(r'[a-z][a-z0-9.]{0,12}(/[a-z0-9._-]{1,8}){0,3}', fullmatch=True)
SECRETS = hypothesis.strategies.from_regex(r'[A-Za-z0-9:._-]{1,16}', fullmatch=True)


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(scheme=SCHEMES, secret=SECRETS, host=HOSTS)
def test_redact_url_removes_the_user_info(scheme: str, secret: str, host: str) -> None:
    redacted = ralphlib.giter.redact_url(f'fetch failed for {scheme}{secret}@{host}: boom')
    assert redacted == f'fetch failed for {scheme}{host}: boom'


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(text=hypothesis.strategies.text())
def test_redact_url_is_idempotent_and_leaves_text_without_at_signs_alone(text: str) -> None:
    once = ralphlib.giter.redact_url(text)
    assert ralphlib.giter.redact_url(once) == once
    if '@' not in text:
        assert once == text


def base_ref_file(ref: str) -> str:
    return json.dumps({'worktree': {'baseRef': ref}})


BASE_REF_FILES = hypothesis.strategies.lists(
    hypothesis.strategies.one_of(
        hypothesis.strategies.none(),
        hypothesis.strategies.just('{not json'),
        hypothesis.strategies.just('[1, 2]'),
        hypothesis.strategies.just('{"worktree": "head"}'),
        hypothesis.strategies.sampled_from(['fresh', 'head']).map(base_ref_file),
    ),
    max_size=5,
)


@hypothesis.settings(max_examples=20, deadline=10000)
@hypothesis.given(contents=BASE_REF_FILES)
def test_claude_worktree_base_ref_is_the_last_valid_setting_or_fresh(contents: list[str | None]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        expected = 'fresh'
        for i, content in enumerate(contents):
            path = pathlib.Path(tmp) / f'settings-{i}.json'
            paths.append(path)
            if content is not None:
                path.write_text(content)
                if '"baseRef"' in content:
                    expected = json.loads(content)['worktree']['baseRef']
        with unittest.mock.patch.object(ralphlib.giter, 'claude_settings_paths', return_value=paths):
            assert ralphlib.giter.claude_worktree_base_ref(unittest.mock.MagicMock()) == expected
