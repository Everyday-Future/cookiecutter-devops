"""

A universal factory for different database types

"""

from config import Config
from api.adapters.database.baseclass import Database
from api.adapters.database.postgres import DatabasePostgres


def get_database(database_type='postgres', **kwargs):
    database_type = database_type or Config.DEFAULT_DB
    if database_type == 'postgres':
        print('connecting to remote db...')
        return DatabasePostgres(**kwargs)
    else:
        raise ValueError(f'Database type {database_type} not recognized')
