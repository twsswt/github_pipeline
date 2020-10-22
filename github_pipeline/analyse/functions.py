from .classes import CloneOrPullGithubRepositories, ClonkinAnalysisGithubRepositories, ExportGitHubRepositoryMetaData


def clone_or_pull(
        repositories,
        local_repositories_path='repositories'):
    return CloneOrPullGithubRepositories(repositories, local_repositories_path)


def perform_clonkin_analysis_on_commits(
        repositories,
        local_repositories_path='repositories',
        database_path='clonkin.db',
        commit_limit=None,
        brute=False):

    return ClonkinAnalysisGithubRepositories(repositories, local_repositories_path, database_path, commit_limit, brute)


def export_github_repository_metadata(
        repositories,
        local_repository_path='repositories',
        database_path='export.db'):

    return ExportGitHubRepositoryMetaData(repositories, local_repository_path, database_path)
