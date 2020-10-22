import logging
import os

from github_pipeline.sample import filter_repositories, repository_status_cache, sample_repositories

logging.basicConfig(level=logging.INFO)

# Create an API token in your GitHub account and set the GITHUB_API_TOKEN to this value.
os.environ['GITHUB_API_TOKEN'] = ''

logging.info("Checking cache...")
logging.info("[%d] cached repositories.", len(repository_status_cache('repositories.db')))

logging.info("Sampling repository IDs randomly and filtering for Java language presence.")


def java_filter(repository):
    languages = repository.get_languages()
    return 'Java' in languages


sample_pipeline = filter_repositories(
    sample_repositories('repositories.db', sample_size=1000),
    java_filter
)


for _ in sample_pipeline:
    pass