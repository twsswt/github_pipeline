import os
import shutil
import unittest

from git import Repo

from github_pipeline.analyse.git_view import GitAtCommit, get_commits_on_branch


class GitViewTestCase(unittest.TestCase):

    def setUp(self):

        def add_content(filename, content, commit_message):
            file_handle = open('test_repository/' + filename, 'w')
            file_handle.write(content)
            file_handle.close()
            self.git_repository.index.add([filename])
            self.git_repository.index.commit(commit_message)

        shutil.rmtree('test_repository', ignore_errors=True)
        os.mkdir('test_repository')
        self.git_repository = Repo.init('test_repository')

        add_content('README.md', '', 'Initial commit')

        feature_branch = self.git_repository.create_head('feature')
        feature_branch.checkout()

        add_content('new_feature.py', 'import os', 'Starting new feature')

        self.git_repository.heads.master.checkout()

        add_content('README.md', '# Test Repository', 'Adds content')

    def test_git_view_checkout_first_commit_and_reverts(self):

        first_commit = list(self.git_repository.iter_commits())[-1]
        first_commit_hexsha = list(self.git_repository.iter_commits())[-1].hexsha

        last_commit_hexsha = list(self.git_repository.iter_commits())[0].hexsha

        with GitAtCommit(self.git_repository, first_commit, restore_after=True):
            current_commit = list(self.git_repository.iter_commits())[0]
            self.assertEqual(first_commit_hexsha, current_commit.hexsha)

        current_commit = list(self.git_repository.iter_commits())[0]
        self.assertEqual(last_commit_hexsha, current_commit.hexsha)

    def test_get_commits_in_master(self):
        commits_in_master = get_commits_on_branch(self.git_repository)
        self.assertEqual(2, len(commits_in_master))

    def test_get_commits_in_unusual_default_branch(self):
        _4 = self.git_repository.create_head('4', commit=self.git_repository.head.commit)
        _4.checkout()
        self.git_repository.delete_head('master')

        commits = get_commits_on_branch(self.git_repository)
        print(commits)

    def tearDown(self):
        self.git_repository.__del__()
        shutil.rmtree('test_repository', ignore_errors=False)


if __name__ == '__main__':
    unittest.main()
