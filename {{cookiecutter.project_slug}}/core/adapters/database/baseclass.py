"""

A central and easy interface to different kinds of databases

"""


class Database:
    def __init__(self, host=None, port=None, dbname=None, user=None, password=None):
        """
        This class acts as just a base class, so none of the functions work,
        they just specify an interface so that different database types are interchangeable
        """
        pass

    def __del__(self):
        """
        Close the connections when the object is destroyed
        """
        raise NotImplementedError('This is the base class for the db. Implement one of the inherited classes instead '
                                  'by using get_database and passing a database type')

    def read_df(self, sql):
        """
        Read a pandas dataframe in from a sql query
        Args:
            sql (): The SQL query that will return the table

        Returns:
            Pandas dataframe with sql results
        """
        raise NotImplementedError('This is the base class for the db. Implement one of the inherited classes instead '
                                  'by using get_database and passing a database type')

    def run_sql(self, sql):
        """
        Run SQL against the target DB
        """
        raise NotImplementedError('This is the base class for the db. Implement one of the inherited classes instead '
                                  'by using get_database and passing a database type')

    def truncate_table(self, table_name):
        """
        Drop all rows in a table by name
        Args:
            table_name (): Name of the table to drop
        """
        raise NotImplementedError('This is the base class for the db. Implement one of the inherited classes instead '
                                  'by using get_database and passing a database type')

    def write_data(self, sql, args_list, table_name=None, do_truncate=False):
        """
        Write data to the SQL database
        Args:
            sql ():
            args_list ():
            table_name (): Name of the table that is being updated in case it needs to be truncated
            do_truncate (): Whether to truncate the table before writing
        """
        raise NotImplementedError('This is the base class for the db. Implement one of the inherited classes instead '
                                  'by using get_database and passing a database type')
