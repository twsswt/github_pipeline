import unittest
import os

from github_pipeline.export.classes import SqliteTable


class SqlTableTestCase(unittest.TestCase):

    def test_two_column_primary_key(self):
        table = SqliteTable('test2.db', 'Test', ['id INT', 'name TEXT', 'address TEXT'], ['id', 'name'])

        table[(1, 'bob')] = ('bob@test.com', )
        self.assertEqual(table[(1, 'bob')], (1, 'bob', 'bob@test.com', ))
        self.assertTrue((1, 'bob') in table)
        os.remove('test2.db')

    def test_one_column_primary_key(self):

        table = SqliteTable('test1.db', 'Test', ['id INT', 'name TEXT', 'address TEXT'], ['id'])
        table[1] = ('bob', 'bob@test.com')
        self.assertEqual(table[1], (1, 'bob', 'bob@test.com', ))
        self.assertTrue(1 in table)
        os.remove('test1.db')


if __name__ == '__main__':
    unittest.main()
