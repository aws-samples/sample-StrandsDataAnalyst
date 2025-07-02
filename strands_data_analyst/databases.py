import re
from abc import ABC, abstractmethod
import sqlite3
from os import path


MIN_EXAMPLES = 3
MAX_DISTINCT_VALUES = 10


class DB(ABC):
    """
    A DB class has to set the DB_TYPE constant, and implement two abstract methods:
    1. get_connection_code(): returning a tuple to open and close a connection to the database.
    2. get_schema(): a dictionary having the table names as keys, and a list of column types as values.
        Each column type is a dictionary containing 3 fields:
        a) name: the name of the column
        b) type: the type of the column
        c) distinct_values: example values of the column
    """
    @abstractmethod
    def get_connection_code(self): pass

    @abstractmethod
    def get_schema(self): pass


CODE_PATTERN = re.compile(r"^[a-zA-Z]?[0-9.\-:]+$")


def is_code(string):
    return re.match(CODE_PATTERN, str(string)) is not None


def get_examples(value_count):
    values = []
    for value, count in value_count:
        values.append(value)
        if count < 2 and len(values) >= MIN_EXAMPLES:
            break
    
    if len(values) > MIN_EXAMPLES and all(map(is_code, values)):
        values = values[:MIN_EXAMPLES]

    return values


class SQLiteDB(DB):
    DB_TYPE = 'SQLite'

    def __init__(self, db_info):
        self.database_source = db_info['db_location']
        if not path.exists(self.database_source):
            raise Exception(f"Missing DB: {self.database_source}")

    def __get_tables(self, cursor):
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return [table[0] for table in cursor.fetchall()]

    def __get_top_distinct_values(self, cursor, table_name, column_name):
        try:
            cursor.execute(f'SELECT "{column_name}", COUNT(*) FROM "{table_name}" GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT {MAX_DISTINCT_VALUES};')
            return get_examples(cursor.fetchall())
        except Exception as e:
            raise Exception(f"Error processing column {column_name} in table {table_name}:\n{e}")

    def __get_table_schema(self, cursor, table_name: str):
        cursor.execute(f'PRAGMA table_info("{table_name}");')

        schema = []
        for col in cursor.fetchall():
            _, name, col_type = col[:3]
            schema.append({
                'name': name,
                'type': col_type,
                'distinct_values': self.__get_top_distinct_values(cursor, table_name, name)
            })
        return schema

    def get_schema(self):
        connection = sqlite3.connect(self.database_source)
        cursor = connection.cursor()
        schema = {table: self.__get_table_schema(cursor, table) for table in self.__get_tables(cursor)}
        connection.close()
        return schema

    def get_connection_code(self):
        return f"""
import sqlite3
db_conn = sqlite3.connect({self.database_source})
""", """
db_conn.close()
"""

DATABASES = {
    'sqlite': SQLiteDB
}
