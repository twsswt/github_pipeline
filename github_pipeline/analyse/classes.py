import logging

from pathlib import Path

from os import makedirs

from urllib.parse import urlparse

from git import Git, NoSuchPathError, Repo

from pygount import ProjectSummary, SourceAnalysis

from clonkin.progress_tracker import ProgressTracker
from clonkin.gherkin_project import gherkin_project_from_paths

from clonkin.gherkin.aaa_violations import reporter as aaa_violations_reporter
from clonkin.gherkin.clones import reporter as clone_reporter
from clonkin.gherkin.lazy_scenario_outlines import reporter as lazy_outlines_reporter
from clonkin.gherkin.lazy_step_examples import reporter as lazy_steps_reporter
from clonkin.gherkin.project import reporter as project_reporter

from github_pipeline.sample.classes import AbstractGithubRepositories
from .git_view import GitAtCommit, get_commits_on_branch

from github_pipeline.export import create_sql_table, create_sql_table_descriptor


logger = logging.getLogger(__name__)


def _guess_default_branch(github_repository, local_repository):
    candidates = \
        [github_repository.default_branch, 'master', 'main', 'develop', 'dev', list(local_repository.heads)[0].name]
    for candidate in candidates:
        if candidate in local_repository.heads:
            return candidate


class CloneOrPullGithubRepositories(AbstractGithubRepositories):

    def __init__(self, source_repositories, repositories_path):
        super().__init__()
        self.source_iter = iter(source_repositories)
        self.repositories_path = repositories_path

    def _get_next_repository(self):
        next_repository = next(self.source_iter)
        try:
            self._clone_or_pull_git_repository(next_repository)
        except Exception:
            logger.warning("Error when synchronizing repository [%d] [%s].",
                           next_repository.id, next_repository.git_url, exc_info=True)
        return next_repository

    def _clone_or_pull_git_repository(self, github_repository):

        git_instance = Git()

        local_path = Path(self.repositories_path + urlparse(github_repository.git_url).path)
        try:
            repo = Repo(local_path)
            logger.info("Repository [%s] already exists, pulling.", str(local_path))
            default_branch = _guess_default_branch(github_repository, repo)
            repo.heads[default_branch].checkout()
            repo.remote('origin').pull()
            return

        except NoSuchPathError:
            logger.info("Cloning [%s].", str(local_path))
            makedirs(local_path.parent, exist_ok=True)
            git_instance.execute(['git', 'clone', github_repository.git_url, str(local_path)])


def _handle_for_file_rename_key_format(key):
    if '{' in key:
        prefix = key.split('{')[0]
        postfix = key.split('}')[1]

        change = key.split('{')[1].split('}')[0].split(' => ')
        source_path = prefix + change[0] + postfix
        destination_path = prefix + change[1] + postfix

    else:
        paths = key.split(' => ')
        source_path = paths[0]
        destination_path = paths[1]

    return source_path, destination_path


def _get_files_changed_in_commit(commit):
    result = set()
    for key in set(commit.stats.files.keys()):
        if ' => ' in key:
            source_path, destination_path = _handle_for_file_rename_key_format(key)
            result.add(source_path)
            result.add(destination_path)
        else:
            result.add(key)
    return result


def _feature_files_are_in_change_set(commit):
    changed_file_paths = _get_files_changed_in_commit(commit)
    for file_path in changed_file_paths:
        if file_path.endswith('.feature'):
            return True
    return False


clonkin_analysis_table_descriptor = create_sql_table_descriptor(
    table_name="ClonkinAnalysisGitHubRepositories",
    columns=[
        "repository_id INT",
        "commit_hexsha TEXT",
        "commit_date INT",

        "lines_count INT",

        "gherkin_files_count INT",
        "unparsed_files_count INT",
        "empty_files_count INT",

        "features_count INT",
        "scenarios_count INT",
        "backgrounds_count INT",

        "given_count INT",
        "when_count INT",
        "then_count INT",
        "steps_count INT",

        "clones_count INT",
        "clone_lines_count INT",
        "clone_rate REAL",

        "aaa_violations_count INT",

        "lazy_outlines_table_count INT",
        "lazy_step_examples_count INT"
    ],
    primary_keys=['repository_id', 'commit_hexsha'],
)


class ClonkinAnalysisGithubRepositories(AbstractGithubRepositories):

    def __init__(self,
                 source_repositories,
                 local_repositories_path,
                 database_path,
                 commit_limit=1,
                 brute_clonkin=False):

        super().__init__()

        self.source_iter = iter(source_repositories)
        self.local_repositories_path = local_repositories_path

        self.database_table = create_sql_table(database_path, clonkin_analysis_table_descriptor)

        self._gherkin_reporters = [
            project_reporter(),
            clone_reporter(),
            aaa_violations_reporter(),
            lazy_outlines_reporter(),
            lazy_steps_reporter()]

        self.commit_limit = commit_limit
        self.brute_clonkin = brute_clonkin

    def _get_next_repository(self):
        next_repository = next(self.source_iter)
        logger.info("Starting analysis on repository [%s] [%d]", next_repository.name, next_repository.id)
        try:
            self._perform_analysis(next_repository)
        except Exception as e:
            logger.warning("Couldn't do clonkin analysis on repository [%s]", next_repository.name, exc_info=True)

        return next_repository

    def _perform_analysis(self, next_repository):
        local_repository_path = self.local_repositories_path + urlparse(next_repository.git_url).path

        git_repository = Repo(local_repository_path)
        default_branch = _guess_default_branch(next_repository, git_repository)
        commits = get_commits_on_branch(git_repository, branch_names=[default_branch], limit=self.commit_limit)
        logging.info("[%d] commits found.", len(commits))

        progress_tracker = ProgressTracker(len(commits), object_type_name='commits')

        last_clonkin_values = (0, ) * 16

        for commit in reversed(commits):
            if (next_repository.id, commit.hexsha) not in self.database_table:

                logger.info("Checking out commit [%s]" % commit.hexsha)
                with GitAtCommit(git_repository, commit):
                    data_values = (commit.authored_date, )
                    data_values += self._perform_pygount_analysis(local_repository_path)
                    if _feature_files_are_in_change_set(commit) or self.brute_clonkin:
                        last_clonkin_values = self._perform_clonkin_analysis(local_repository_path)
                    data_values += last_clonkin_values

                self.database_table[(next_repository.id, commit.hexsha)] = data_values

            progress_tracker.processed_object()

    def _perform_clonkin_analysis(self, local_repository_path):
        logger.info("Starting clonkin analysis on [%s].", local_repository_path)
        feature_file_paths = list(Path(local_repository_path).rglob("*.feature"))
        gherkin_project = gherkin_project_from_paths(feature_file_paths)

        for reporter in self._gherkin_reporters:
            gherkin_project.add_report(reporter, False)

        result = list()
        for smell_report in gherkin_project.reports:
            for value in smell_report.project_report_values():
                result.append(value)

        return tuple(result)

    def _perform_pygount_analysis(self, local_repository_path):
        pygcount_project_summary = ProjectSummary()

        source_paths = list(Path(local_repository_path).rglob("*"))

        logger.info("Starting pygount analysis on [%d] source paths in [%s].",
                    len(source_paths), local_repository_path)

        for source_path in source_paths:
            if source_path.is_file() and 'src-min' not in str(source_path):
                source_analysis = SourceAnalysis.from_file(str(source_path), '')
                pygcount_project_summary.add(source_analysis)

        total_lines = pygcount_project_summary.total_code_count
        return total_lines,


repository_meta_data_table_descriptor = create_sql_table_descriptor(
    table_name='GitHubRepositoryMetaData',
    columns=[
        'repository_id INT',
        'name TEXT',
        'url TEXT',

        'main_language TEXT',
        'total_bytes INT',

        'total_contributors INT',

        'last_commit_hexsha TEXT',
        'total_commits INT',
        'first_commit_date INT',
        'last_commit_date INT',

        'total_issues INT',
        'open_issues INT',
        'closed_issues INT',
        'all_pull_requests INT',
        'open_pull_requests INT',
        'closed_pull_requests INT'],
    primary_keys=['repository_id']
)


class ExportGitHubRepositoryMetaData(AbstractGithubRepositories):

    def __init__(self, source_repositories, local_repositories_path, database_path):
        super().__init__()
        self.source_iter = iter(source_repositories)
        self.local_repositories_path = local_repositories_path

        self.database_table = create_sql_table(database_path, repository_meta_data_table_descriptor)

    def _get_next_repository(self):
        next_repository = next(self.source_iter)
        try:
            if next_repository.id not in self.database_table:
                logger.info("Retrieving meta data for repository [%s] [%d].", next_repository.name, next_repository.id)
                self._export_repository_meta_data(next_repository)
        except Exception as e:
            logger.warning("Couldn't retrieve metadata for repository [%s]", next_repository.name, exc_info=True)

        return next_repository

    def _export_repository_meta_data(self, github_repository):
        local_repository_path = self.local_repositories_path + urlparse(github_repository.git_url).path
        git_repository = Repo(local_repository_path)
        default_branch = _guess_default_branch(github_repository, git_repository)
        commits = get_commits_on_branch(git_repository, branch_names=[default_branch])

        data_values = (
            github_repository.name,
            github_repository.git_url,

            github_repository.language,
            sum(github_repository.get_languages().values()),

            github_repository.get_contributors().totalCount,

            commits[0].hexsha,
            len(commits),
            commits[-1].authored_date,
            commits[0].authored_date,

            github_repository.get_issues(state='all').totalCount,
            github_repository.open_issues_count,
            github_repository.get_issues(state='closed').totalCount,
            github_repository.get_pulls(state='all').totalCount,
            github_repository.get_pulls(state='open').totalCount,
            github_repository.get_pulls(state='closed').totalCount)

        self.database_table[github_repository.id] = data_values
