import logging

from github import GithubException

from github_pipeline.export import create_sql_table, create_sql_table_descriptor

logger = logging.getLogger('sample.functions')

_repository_caches = dict()


cache_table_descriptor = \
    create_sql_table_descriptor('RepositoryCache', ['repository_id INT', 'status TEXT'], ['repository_id'])


def repository_status_cache(cache_file_path='repository_cache.db'):
    global _repository_caches
    if cache_file_path not in _repository_caches:
        _repository_caches[cache_file_path] = create_sql_table(cache_file_path, cache_table_descriptor)
    return _repository_caches[cache_file_path]


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


def log_cache_size(cache_file_path):
    logger.info("Checking cache...")
    logger.info("...[%d] cached repositories.", len(repository_status_cache(cache_file_path)))



