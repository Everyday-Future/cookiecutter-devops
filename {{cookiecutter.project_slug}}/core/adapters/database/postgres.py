"""

Database connector for PostgresQL

"""

import numpy as np
import pandas as pd
import psycopg2 as pg
from psycopg2 import extensions, extras
from psycopg2.extensions import register_adapter, AsIs
from api.adapters.database.baseclass import Database
from api.utils import timemethod
from config import Config


def nan_to_null(f, _null=extensions.AsIs('NULL'), _float=extensions.Float):
    if f != f:
        return _null
    else:
        return _float(f)


register_adapter(float, nan_to_null)
register_adapter(np.int32, AsIs)
register_adapter(np.int64, AsIs)
register_adapter(np.bool_, AsIs)
register_adapter(np.datetime64, AsIs)
register_adapter(np.NaN, AsIs)


# noinspection PyMissingConstructor
class DatabasePostgres(Database):
    """
    Adapter to connect to postgresql databases
    """

    def __init__(self, host=None, port=None, dbname=None, user=None, password=None):
        """
        Instantiate the adapter with connection params that fall back to Config values
        Args:
            host ():
            port ():
            dbname ():
            user ():
            password ():
        """
        self.conn = pg.connect(host=host or Config.DB_HOST,
                               port=port or Config.DB_PORT,
                               dbname=dbname or Config.DB_NAME,
                               user=user or Config.DB_USER,
                               password=password or Config.DB_PASS)
        self.cursor = self.conn.cursor()

    def __del__(self):
        """
        Close the connections when the object is destroyed
        """
        if self.cursor is not None:
            self.cursor.close()
        if self.conn is not None:
            self.conn.close()

    def read_df(self, sql):
        """
        Read a pandas dataframe in from a sql query
        Args:
            sql (): The SQL query that will return the table

        Returns:
            Pandas dataframe with sql results
        """
        table = pd.read_sql_query(sql, self.conn)
        self.conn.commit()
        return table

    def run_sql(self, sql):
        """
        Run SQL against the target DB
        """
        self.cursor.execute(sql)
        self.conn.commit()

    def truncate_table(self, table_name):
        """
        Drop all rows in a table by name
        Args:
            table_name (): Name of the table to drop
        """
        if Config.BLOCK_WRITE_DB is True:
            return False
        self.run_sql(f"TRUNCATE TABLE {table_name}")

    @timemethod
    def write_data(self, sql, args_list, table_name=None, do_truncate=False):
        """
        Write data to the SQL database
        Args:
            sql ():
            args_list ():
            table_name (): Name of the table that is being updated in case it needs to be truncated
            do_truncate (): Whether to truncate the table before writing
        """
        if Config.BLOCK_WRITE_DB is True:
            return False
        if table_name is not None and do_truncate is True:
            self.truncate_table(table_name=table_name)
        extras.execute_batch(self.cursor, sql, args_list, page_size=1000)
        self.conn.commit()

    def list_tables(self):
        """
        Get tables as list of tuples like [(name, row_count, schema)]
        for example [('user', 17, 'public'), ('product', 22, 'public'), ...]
        :return:
        :rtype:
        """
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
