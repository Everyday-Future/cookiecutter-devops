"""
Database connector for PostgreSQL
"""

import time
import logging
import numpy as np
import pandas as pd
import psycopg2 as pg
from psycopg2 import extensions
from psycopg2.extensions import register_adapter, AsIs
from core.adapters.database.baseclass import Database
from config import Config
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from psycopg2.extensions import connection as PgConnection
from psycopg2.extensions import cursor as PgCursor
from typing import List, Tuple, Dict, Generator, Optional, Set, Any

logger = logging.getLogger(__name__)


def nan_to_null(f, _null=extensions.AsIs('NULL'), _float=extensions.Float):
    """
    Convert NaN to NULL for database insertion.

    :param f: The float value to check.
    :param _null: The NULL value for the database.
    :param _float: The float type for the database.
    :return: The value to insert into the database.
    """
    if f != f:
        return _null
    else:
        return _float(f)


register_adapter(float, nan_to_null)
register_adapter(np.int32, AsIs)
register_adapter(np.int64, AsIs)
register_adapter(np.bool_, AsIs)
register_adapter(np.datetime64, AsIs)
register_adapter(np.nan, AsIs)


class DatabasePostgres(Database):
    """
    Adapter to connect to PostgreSQL databases.

    :param db_url: The database URL.
    :param eager_commit: Whether to commit after each operation.
    """
    TABLE_DATA = [{'name': 'user', 'id_col': 'id'}]

    def __init__(self, db_url: str, eager_commit: bool = True):
        super().__init__()
        self.db_url: str = db_url
        self.connector: Optional[PgConnection] = None
        self.cursor: Optional[PgCursor] = None
        self.engine: Optional[Engine] = None
        self.eager_commit: bool = eager_commit

    def __enter__(self) -> 'DatabasePostgres':
        """
        Enter the runtime context related to this object.

        :return: The database connector object.
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit the runtime context related to this object.

        :param exc_type: The exception type.
        :param exc_value: The exception value.
        :param traceback: The traceback object.
        """
        self.stop()

    def start(self) -> PgCursor:
        """
        Start the database connection.

        :return: The database cursor.
        """
        if self.connector is None or self.cursor is None:
            self.connector = pg.connect(self.db_url)
            self.cursor = self.connector.cursor()
            self.engine = create_engine(self.db_url)
        return self.cursor

    def stop(self):
        """
        Stop the database connection.
        """
        if self.connector is not None:
            if self.eager_commit:
                self.connector.commit()
            self.cursor.close()
            self.connector.close()
            self.engine.dispose()
            self.connector = None
            self.cursor = None
            self.engine = None

    def commit(self):
        """
        Commit the current transaction.
        """
        if self.connector:
            self.connector.commit()

    def execute(self, statement: str, parameters: Optional[Tuple] = None):
        """
        Execute a SQL statement.

        :param statement: The SQL statement to execute.
        :param parameters: The parameters for the SQL statement.
        """
        try:
            self.cursor.execute(statement, parameters)
            if self.eager_commit:
                self.commit()
        except Exception as e:
            logger.error(f"Error executing statement: {statement} - {e}")
            self.rollback()
            raise

    def rollback(self):
        """
        Rollback the current transaction.
        """
        if self.connector:
            self.connector.rollback()

    def list_tables(self) -> List[Tuple[str, int, str]]:
        """
        List all tables in the database.

        :return: A list of tuples containing table names, row counts, and schemas.
        """
        try:
            self.cursor.execute("""
            WITH tbl AS
              (SELECT table_schema,
                      TABLE_NAME
               FROM information_schema.tables
               WHERE TABLE_NAME not like 'pg_%'
                 AND table_schema in ('public'))
            SELECT TABLE_NAME,
                   (xpath('/row/c/text()', query_to_xml(format('select count(*) as c from %I.%I', table_schema, TABLE_NAME), FALSE, TRUE, '')))[1]::text::int AS rows_n,
                   table_schema
            FROM tbl
            ORDER BY rows_n DESC;
            """)
            return list(self.cursor.fetchall())
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            raise

    @classmethod
    def get_table_data(cls) -> List[Dict[str, str]]:
        """
        Get the table schema.

        :return: A list of dictionaries containing table names and ID columns.
        """
        return cls.TABLE_DATA

    def get_table_df(self, sql: str) -> pd.DataFrame:
        """
        Read a pandas DataFrame from a SQL query.

        :param sql: The SQL query to execute.
        :return: A pandas DataFrame with the SQL results.
        """
        table = pd.read_sql_query(sql, self.connector)
        self.connector.commit()
        return table

    @classmethod
    def get_id_col(cls, table_name: str) -> str:
        """
        Get the ID column for a given table.

        :param table_name: The name of the table.
        :return: The ID column of the table.
        :raises ValueError: If the table is not found.
        """
        table_data = cls.get_table_data()
        for table in table_data:
            if table['name'] == table_name:
                return table['id_col']
        raise ValueError(f"Table {table_name} not found in table data")

    def get_table(self, table_name: str) -> pd.DataFrame:
        """
        Get the data from a table as a pandas DataFrame.

        :param table_name: The name of the table.
        :return: A pandas DataFrame with the table data.
        """
        try:
            return pd.read_sql_query(f'SELECT * FROM "{table_name}"', con=self.engine)
        except Exception as e:
            logger.error(f"Error getting table {table_name}: {e}")
            raise

    def count_table(self, table_name: str) -> int:
        """
        Count the number of rows in a table.

        :param table_name: The name of the table.
        :return: The number of rows in the table.
        """
        try:
            select_statement = f'SELECT COUNT(*) FROM "{table_name}"'
            self.execute(select_statement)
            return self.cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error counting table {table_name}: {e}")
            raise

    @staticmethod
    def chunks(lst: List[Any], n: int) -> Generator[List[Any], None, None]:
        """
        Yield successive n-sized chunks from lst.

        :param lst: The list to divide into chunks.
        :param n: The size of each chunk.
        :yield: A chunk of the list.
        """
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    def delete_by_ids(self, table_name: str, id_col_name: str, id_set: Set[int], chunksize: int = 100):
        """
        Delete rows by IDs from a table.

        :param table_name: The name of the table.
        :param id_col_name: The name of the ID column.
        :param id_set: A set of IDs to delete.
        :param chunksize: The number of rows to delete at a time.
        :return: False if writing to the database is blocked, otherwise None.
        """
        if Config.BLOCK_WRITE_DB is True:
            return False
        start_time = time.time()
        try:
            for chunk in self.chunks(list(id_set), chunksize):
                self.execute(
                    f'DELETE FROM "{table_name}" WHERE {id_col_name} IN %s', (tuple(chunk),))
            logger.info(f'{table_name} done! - {time.time() - start_time}')
        except Exception as e:
            logger.error(f"Error deleting by ids in table {table_name}: {e}")
            raise

    def clear_table(self, table_name: str, id_col: str):
        """
        Clear all rows from a table.

        :param table_name: The name of the table.
        :param id_col: The name of the ID column.
        :return: False if writing to the database is blocked, otherwise None.
        """
        if Config.BLOCK_WRITE_DB is True:
            return False
        try:
            before_len = self.count_table(table_name)
            delete_statement = f'TRUNCATE TABLE {table_name}'
            self.execute(delete_statement)
            logger.info(f"Count of rows in table={table_name} from {before_len} to {self.count_table(table_name)}")
        except Exception as e:
            logger.error(f"Error clearing table {table_name}: {e}")
            raise

    def clear_db(self):
        """
        Clear all tables in the database.

        :return: False if writing to the database is blocked, otherwise None.
        """
        if Config.BLOCK_WRITE_DB is True:
            return False
        try:
            table_data = self.get_table_data()
            for table_cfg in table_data[::-1]:
                table_name = table_cfg['name']
                id_col = table_cfg['id_col']
                self.clear_table(table_name, id_col)
        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            raise

    def reset_max_id(self, table_name: str, id_col: str):
        """
        Reset the maximum ID for a table.

        :param table_name: The name of the table.
        :param id_col: The name of the ID column.
        """
        try:
            set_max_id = f'SELECT setval(\'{table_name}_{id_col}_seq\', (SELECT MAX({id_col}) FROM "{table_name}")+1)'
            self.execute(set_max_id)
        except Exception as e:
            logger.error(f"Error resetting max id for table {table_name}: {e}")
            raise

    def push_table(self, table_df: pd.DataFrame, table_name: str, id_col: str):
        """
        Push a pandas DataFrame into a table.

        :param table_df: The pandas DataFrame to push.
        :param table_name: The name of the table.
        :param id_col: The name of the ID column.
        """
        try:
            dtype = {'data': sqlalchemy.types.JSON,
                     'responses': sqlalchemy.types.JSON,
                     'order_confirmation': sqlalchemy.types.JSON,
                     'config': sqlalchemy.types.JSON,
                     'attachments': sqlalchemy.types.JSON}
            dtype = {key: val for key, val in dtype.items() if key in table_df.columns}
            table_df.to_sql(table_name, con=self.engine, index=False, if_exists="append",
                            dtype=dtype, chunksize=10000, method='multi')
            self.reset_max_id(table_name, id_col)
        except Exception as e:
            logger.error(f"Error pushing table {table_name}: {e}")
            raise

    def push_db(self, update_dict: Dict[str, pd.DataFrame]):
        """
        Push a dictionary of pandas DataFrames into the database.

        :param update_dict: A dictionary of table names and pandas DataFrames.
        """
        try:
            for table_name, table_df in update_dict.items():
                logger.info(f'Clearing {table_name}')
                self.clear_table(table_name, self.get_id_col(table_name))
            for table_name, table_df in reversed(list(update_dict.items())):
                logger.info(f'Migrating {table_name}')
                if table_df is not None:
                    self.push_table(table_df, table_name, self.get_id_col(table_name))
            logger.debug('PostgresConnector.push_db() complete!')
        except Exception as e:
            logger.error(f"Error pushing database: {e}")
            raise

    def cache_table_counts(self):
        """
        Cache the row counts for all tables in the database.
        """
        self._table_counts_cache = {}
        for table_name, _, _ in self.list_tables():
            self._table_counts_cache[table_name] = self.count_table(table_name)

    def get_cached_table_count(self, table_name: str) -> int:
        """
        Get the cached row count for a table.

        :param table_name: The name of the table.
        :return: The cached row count.
        """
        return self._table_counts_cache.get(table_name, -1)

    def log_table_stats(self):
        """
        Log the row counts for all tables in the database.
        """
        for table_name, row_count in self._table_counts_cache.items():
            logger.info(f"Table {table_name} has {row_count} rows.")
