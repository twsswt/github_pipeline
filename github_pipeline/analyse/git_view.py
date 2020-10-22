from git import Repo


class GitAtCommit:

    def __init__(self, git_repository: Repo, commit, restore_after=False):

        self._git_repository = git_repository
        self._target_commit = commit
        self._restore_after = restore_after

        self._state_to_restore = None

    def __enter__(self):
        if self._restore_after:
            self._state_to_restore = next(self._git_repository.iter_commits())

        self._git_repository.git.checkout(self._target_commit, force=True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._restore_after:
            result = self._git_repository.git.checkout(self._state_to_restore)


def get_commits_on_branch(git_repository: Repo, branch_names=None, limit=None):
    _branch_names = ['master', 'develop', 'main', 'dev'] if branch_names is None else branch_names

    result = list()

    for branch_name in _branch_names:
        if branch_name in git_repository.heads:
            current = git_repository.heads[branch_name].commit
            result.append(current)

            while len(current.parents) > 0 and (limit is None or len(result) < limit):
                result.append(current.parents[0])
                current = current.parents[0]

            return result

    return None


