from github import GithubException

from github_pipeline.export import create_sql_table, create_sql_table_descriptor

from .classes import CachedGithubRepositories, FilteredGithubRepositories, ReplaceGithubRepositories, \
    SampledGithubRepositories, SearchGithubRepositories, WriteToCacheGithubRepositories


_repository_caches = dict()


cache_table_descriptor = \
    create_sql_table_descriptor('RepositoryCache', ['repository_id INT', 'status TEXT'], ['repository_id'])


def repository_status_cache(cache_file_path='repository_cache.db'):
    global _repository_caches
    if cache_file_path not in _repository_caches:
        _repository_caches[cache_file_path] = create_sql_table(cache_file_path, cache_table_descriptor)
    return _repository_caches[cache_file_path]


def search_repositories(query):
    return SearchGithubRepositories(query)


def sample_repositories(
        filename='repository_cache.db',
        sample_size=1000000,
        max_repository_id=251108600,
        seed=1):
    return SampledGithubRepositories(repository_status_cache(filename), sample_size, max_repository_id, seed)


def cached_repositories(cache_file_path='repository_cache.db', repository_ids=None):
    cache = repository_status_cache(cache_file_path)
    cached_github_repositories = CachedGithubRepositories(cache, repository_ids)
    return cached_github_repositories


def filter_repositories(repositories, filter):
    return FilteredGithubRepositories(repositories, filter, repository_status_cache())


def filter_for_gherkin_projects(repositories):

    def gherkin_filter(repository):
        languages = repository.get_languages()
        return 'Gherkin' in languages

    return filter_repositories(repositories, gherkin_filter)


def filter_for_duplicates(repositories):

    already_seen = set()

    def not_already_seen(repository):
        result = repository.id not in already_seen
        already_seen.add(repository.id)
        return result

    return FilteredGithubRepositories(repositories, not_already_seen)


def replace_forks_with_parents(repositories):

    def replace_fork_repository_with_original(repository):
        while repository.fork:
            repository = repository.parent
        return repository

    return ReplaceGithubRepositories(repositories, replace_fork_repository_with_original)


def filter_for_real_projects(repositories):

    def real_projects_filter(repository):

        try:
            total_commits = repository.get_commits().totalCount
            total_contributors = repository.get_contributors().totalCount

            is_collaborative_open_source = total_commits >=6 and total_contributors >= 2
            is_useful_to_someone = repository.watchers_count >= 1 or repository.forks_count >= 1
            is_large_deposition = sum(repository.get_languages().values()) >= 100000
            return (is_collaborative_open_source and is_useful_to_someone) or is_large_deposition
        except GithubException:
            return False

    return FilteredGithubRepositories(repositories, real_projects_filter)


def write_to_cache(repositories, cache_file_path):
    github_repository_cache = repository_status_cache(cache_file_path)
    return WriteToCacheGithubRepositories(repositories, github_repository_cache)

