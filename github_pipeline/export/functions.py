from .classes import SqliteTable, SqliteTableDescriptor


def create_sql_table(path, table_descriptor):
    return SqliteTable(path, table_descriptor)


def create_sql_table_descriptor(table_name, columns, primary_keys):
    return SqliteTableDescriptor(table_name, columns, primary_keys)
