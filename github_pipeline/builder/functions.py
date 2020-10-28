from .classes import PipelineBuilder

from github_pipeline.sample import SearchGithubRepositories, SampledGithubRepositories, CachedGithubRepositories,\
    repository_status_cache


def search_repositories(query):
    search_github_repositories = SearchGithubRepositories(query)
    return PipelineBuilder(search_github_repositories)


def sample_repositories(
        filename='repository_cache.db',
        sample_size=1000000,
        max_repository_id=251108600,
        seed=1):
    sampler = SampledGithubRepositories(repository_status_cache(filename), sample_size, max_repository_id, seed)
    return PipelineBuilder(sampler)


def cached_repositories(cache_file_path='repository_cache.db', repository_ids=None):
    cache = repository_status_cache(cache_file_path)
    cached_github_repositories = CachedGithubRepositories(cache, repository_ids)
    return PipelineBuilder(cached_github_repositories)
