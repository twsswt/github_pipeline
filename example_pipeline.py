import logging
import os

from github_pipeline.builder import sample_repositories
from github_pipeline.sample import repository_status_cache

logging.basicConfig(level=logging.INFO)

# Create an API token in your GitHub account and set the GITHUB_API_TOKEN to this value.
os.environ['GITHUB_API_TOKEN'] = ''

logging.info("Checking cache...")
logging.info("[%d] cached repositories.", len(repository_status_cache('repositories.db')))

logging.info("Sampling repository IDs randomly and filtering for Java language presence.")


sample_repositories('repositories.db', sample_size=100)\
    .filter_repositories(lambda repository: 'Java' in repository.get_languages())\
    .execute()
