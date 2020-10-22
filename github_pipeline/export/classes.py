import sqlite3


class _SqliteContextManager:

    def __init__(self, database_file_path, table_name, columns, primary_keys):
        self._database_file_path = database_file_path
        self._table_name = table_name
        self._columns = columns
        self._primary_keys = primary_keys

    def __enter__(self):
        self.connection = sqlite3.connect(self._database_file_path)
        cursor = self.connection.cursor()

        query = \
            f'''
             CREATE TABLE IF NOT EXISTS {self._table_name} 
             (
              {','.join(self._columns)}
              , PRIMARY KEY({','.join(self._primary_keys)})
             )
             WITHOUT ROWID
             '''
        cursor.execute(query)
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.close()


class SqliteTable:

    def __init__(self, database_file_path, table_name, columns, primary_keys):
        self._database_file_path = database_file_path
        self._table_name = table_name
        self._columns = columns
        self._primary_keys = primary_keys

    @property
    def _index_condition(self):
        return ' AND '.join([key + ' = ? ' for key in self._primary_keys])

    def _create_sqlite_connection(self):
        return _SqliteContextManager(self._database_file_path, self._table_name, self._columns, self._primary_keys)

    def __contains__(self, item):
        _item = (item, ) if not isinstance(item, tuple) else item
        with self._create_sqlite_connection() as connection:
            cursor = connection.cursor()

            query_string = (
                f'''
                SELECT *
                FROM {self._table_name}
                WHERE {self._index_condition}
                '''
            )

            query_result = cursor.execute(query_string, _item).fetchall()
            return len(query_result) > 0

    def __len__(self):
        with self._create_sqlite_connection() as connection:

            cursor = connection.cursor()

            query_string = (
                f'''
                SELECT COUNT(*)
                FROM {self._table_name}
                '''
            )
            query_result = cursor.execute(query_string).fetchall()
            return query_result[0][0]

    def __getitem__(self, item):
        _item = (item, ) if not isinstance(item, tuple) else item
        with self._create_sqlite_connection() as connection:

            cursor = connection.cursor()

            query_string = (
                f'''
                SELECT *
                FROM {self._table_name}
                WHERE {self._index_condition}
                '''
            )

            query_result = cursor.execute(query_string, _item).fetchall()
            if len(query_result) > 0:
                return query_result[0]
            else:
                raise IndexError

    @property
    def field_names(self):
        return [field.split(' ')[0] for field in self._columns]

    def __setitem__(self, item, values):
        _item = (item, ) if not isinstance(item, tuple) else item

        with self._create_sqlite_connection() as connection:

            cursor = connection.cursor()

            question_marks = ','.join(['?'] * (len(_item) + len(values)))

            query_string = (
                f'''
                REPLACE INTO {self._table_name} (
                 {','.join(self.field_names)}
                )
                VALUES({question_marks});

                '''
            )
            cursor.execute(query_string, _item + values)
            connection.commit()

    def keys(self):
        with self._create_sqlite_connection() as connection:

            cursor = connection.cursor()

            query_string = (
                f'''
                SELECT {','.join(self._primary_keys)}
                FROM {self._table_name};
                '''
            )
            return [t for t in cursor.execute(query_string).fetchall()]