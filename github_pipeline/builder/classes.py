import logging

from github import GithubException, Repository

from github_pipeline.sample import FilteredGithubRepositories, ReplaceGithubRepositories, \
    WriteToCacheGithubRepositories, repository_status_cache

from github_pipeline.analyse import CloneOrPullGithubRepositories, ExportGitHubRepositoryMetaData, \
    ClonkinAnalysisGithubRepositories


logger = logging.getLogger(__name__)


class PipelineBuilder:
    def __init__(self, source):
        self._source = source

    def filter_repositories(self, repository_filter, cache_file_path=None):
        if cache_file_path is None:
            self._source = FilteredGithubRepositories(self._source, repository_filter)
        else:
            github_repository_cache = repository_status_cache(cache_file_path)
            self._source = FilteredGithubRepositories(self._source, repository_filter, github_repository_cache)
        return self

    def replace_repositories(self, replacer):
        self._source = ReplaceGithubRepositories(self._source, replacer)
        return self

    def clone_or_pull(self, local_repositories_path='repositories'):
        self._source = CloneOrPullGithubRepositories(self._source, local_repositories_path)
        return self

    def export_github_repository_metadata(
        self,
        local_repositories_path='repositories',
        database_path='export.db'):

        self._source = ExportGitHubRepositoryMetaData(self._source, local_repositories_path, database_path)
        return self

    def perform_clonkin_analysis_on_commits(
            self,
            local_repositories_path='repositories',
            database_path='clonkin.db',
            commit_limit=None,
            brute=False):

        self._source = ClonkinAnalysisGithubRepositories(
            self._source, local_repositories_path, database_path, commit_limit, brute)
        return self

    def write_to_cache(self, cache_file_path):
        github_repository_cache = repository_status_cache(cache_file_path)
        self._source = WriteToCacheGithubRepositories(self._source, github_repository_cache)
        return self

    def filter_for_duplicates(self):

        already_seen = set()

        def not_already_seen(repository):
            result = repository.id not in already_seen
            already_seen.add(repository.id)
            return result

        return self.filter_repositories(not_already_seen)

    def replace_forks_with_parents(self):

        def replace_fork_repository_with_original(repository):
            while repository.fork:
                repository = repository.parent
            return repository

        return self.replace_repositories(replace_fork_repository_with_original)

    def replace_parents_with_fork(self, condition=lambda repository: True):

        def find_matching_fork(repository: Repository):

            search_queue = list()
            search_queue.append(repository)

            while len(search_queue) > 0:
                candidate = search_queue.pop(0)
                logger.debug("Testing candidate for replacement of parent [%d] [%s].",
                             candidate.id, candidate.git_url)

                if condition(candidate):
                    return candidate
                elif candidate.forks:
                    try:
                        for fork in candidate.get_forks():
                            search_queue.append(fork)
                    except GithubException:
                        pass

            return None

        return self.replace_repositories(find_matching_fork)

    def execute(self):
        for _ in self._source:
            pass
