import logging

import random

from github import GithubException

from github_pipeline.api_wrapper import rate_limited_github_instance


logger = logging.getLogger(__name__)


class _RepositoryIterator:

    def __init__(self, repositories):
        self.repositories = repositories
        self.index = 0

    def __next__(self):
        try:
            return self.repositories[self.index]
        except IndexError:
            raise StopIteration
        finally:
            self.index += 1


class AbstractGithubRepositories:

    logger = logging.getLogger(__name__)

    def __init__(self):
        self.samples = list()

    def __getitem__(self, item):
        while item >= len(self.samples):
            repository = self._get_next_repository()
            if repository is None:
                break
            else:
                self.samples.append(repository)

        if item < len(self.samples):
            return self.samples[item]
        else:
            raise IndexError

    def __len__(self):
        for _ in self:
            pass
        return len(self.samples)

    def __iter__(self):
        return _RepositoryIterator(self)

    def _get_next_repository(self):
        raise NotImplemented


class CachedGithubRepositories(AbstractGithubRepositories):

    def __init__(self, repository_cache, repository_ids=None):
        super().__init__()
        self.repository_cache = repository_cache
        self.index = 0
        self.repository_ids = \
            repository_ids if repository_ids is not None else [t[0] for t in repository_cache.keys()]

        self.github_instance = rate_limited_github_instance()

    def _get_next_repository(self):
        try:
            while True:
                repository_id = self.repository_ids[self.index]
                try:
                    return self.github_instance.get_repo(repository_id)
                except GithubException:
                    logger.warning("Couldn't retrieve cached repository [%d].", repository_id, exc_info=True)
                finally:
                    self.index += 1

        except IndexError:
            logger.warning("No more repositories in cache.")
            return None


class SearchGithubRepositories(AbstractGithubRepositories):

    def __init__(self, query):

        super().__init__()

        self.github_instance = rate_limited_github_instance()
        self.query_result_iter = iter(self.github_instance.search_repositories(query))

    def _get_next_repository(self):
        try:
            return next(self.query_result_iter)
        except StopIteration:
            return None


class SampledGithubRepositories(AbstractGithubRepositories):

    def __init__(self, repository_cache, sample_size=1000000, max_repository_id=251108600, seed=1):

        super().__init__()

        self.repository_cache = repository_cache

        self.sample_size = sample_size
        self.samples_tested = 0

        self.max_repository_id = max_repository_id
        self._random = random.Random(seed)

        self.github_instance = rate_limited_github_instance()

    def _get_next_repository(self):

        while self.samples_tested < self.sample_size:
            self.samples_tested += 1

            repository_id = self._random.randint(0, self.max_repository_id)
            cache_key = repository_id
            if cache_key not in self.repository_cache or self.repository_cache[cache_key]['status'] == 'Match':

                logger.debug("Retrieving repository [%d] ...", repository_id)
                try:
                    repository = self.github_instance.get_repo(repository_id)
                    logger.debug("...found.")
                    return repository

                except GithubException:
                    self.repository_cache[cache_key] = 'Not_Found'
                    logger.debug("...not found.")
            else:
                reason = self.repository_cache[cache_key]['status']
                logger.debug('Skipping repository [%d] as [%s].', repository_id, reason)

        return None


class FilteredGithubRepositories(AbstractGithubRepositories):

    def __init__(self, source_repositories, repo_filter: lambda repository: True, repository_cache=None):
        super().__init__()
        self.source_iter = iter(source_repositories)
        self.repo_filter = repo_filter
        self.repository_cache = repository_cache

        self.samples = list()

    def is_match(self, repository):
        if self.repository_cache:
            cache_key = str(repository.id)
            if cache_key not in self.repository_cache:

                _match = False
                try:
                    _match = self.repo_filter(repository)
                except GithubException:
                    logger.warning("Couldn't evaluate filter [%s] on repository [%d].",
                                   self.repo_filter.__name__, repository.id)

                self.repository_cache[cache_key] = 'Match' if _match else 'No_Match'

            return self.repository_cache[cache_key]['status'] == 'Match'
        else:
            return self.repo_filter(repository)

    def _get_next_repository(self):
        try:
            next_candidate = next(self.source_iter)
            while not self.is_match(next_candidate):
                logger.info("Skipping repository [%d] due to [%s]", next_candidate.id, self.repo_filter.__name__)
                next_candidate = next(self.source_iter)
            return next_candidate
        except StopIteration:
            return None


class ReplaceGithubRepositories(AbstractGithubRepositories):

    def __init__(self, source_repositories, repo_replacer: lambda repository: repository):
        super().__init__()
        self.source_iter = iter(source_repositories)
        self.repo_replacer = repo_replacer

    def _get_next_repository(self):
        next_repository = next(self.source_iter)
        logger.debug("Looking for matching replacement fork for [%d] [%s].",
                     next_repository.id, next_repository.git_url)

        replacement = self.repo_replacer(next_repository)
        logger.debug("Replacing [%d] with [%d].", next_repository.id, replacement.id)

        return replacement


class WriteToCacheGithubRepositories(AbstractGithubRepositories):

    def __init__(self, source_repositories, repository_cache):
        super().__init__()
        self.source_iter = iter(source_repositories)
        self.repository_cache = repository_cache

    def _get_next_repository(self):
        next_repository = next(self.source_iter)
        self.repository_cache[str(next_repository.id)] = 'MATCH'
        return next_repository
