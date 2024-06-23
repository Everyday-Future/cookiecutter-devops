import pytest
import logging
import psycopg2.errors
import pandas as pd
from config import Config
from core.adapters.database.postgres import DatabasePostgres


@pytest.fixture(scope="function")
def db_connector():
    Config.BLOCK_WRITE_DB = False
    connector = DatabasePostgres(Config.SQLALCHEMY_DATABASE_URI)
    connector.start()
    # Set up the test database schema
    setup_database(connector)
    yield connector
    # Teardown the test database
    teardown_database(connector)
    connector.stop()
    Config.BLOCK_WRITE_DB = True


def setup_database(connector):
    with connector.connector.cursor() as cursor:
        # noinspection PyUnresolvedReferences
        try:
            cursor.execute("""TRUNCATE TABLE test_table""")
        except psycopg2.errors.UndefinedTable:
            connector.connector.rollback()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50),
            value INTEGER
        );
        INSERT INTO test_table (id, name, value) VALUES (0, 'test1', 100), (1, 'test2', 200), (2, 'test3', 300)
        ON CONFLICT DO NOTHING;
        """)
        connector.connector.commit()


def teardown_database(connector):
    with connector.connector.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS test_table;")
        connector.connector.commit()


def test_start_stop(db_connector):
    assert db_connector.connector is not None
    assert db_connector.cursor is not None
    db_connector.stop()
    assert db_connector.connector is None
    assert db_connector.cursor is None
    db_connector.start()


def test_list_tables(db_connector):
    tables = db_connector.list_tables()
    assert len(tables) > 0
    assert 'test_table' in [table[0] for table in tables]


def test_get_table(db_connector):
    df = db_connector.get_table('test_table')
    assert isinstance(df, pd.DataFrame)
    assert not df.empty


def test_count_table(db_connector):
    count = db_connector.count_table('test_table')
    assert count == 3


def test_delete_by_ids(db_connector):
    ids_to_delete = {1, 2}
    db_connector.delete_by_ids('test_table', 'id', ids_to_delete)
    count = db_connector.count_table('test_table')
    assert count == 1


def test_clear_table(db_connector):
    db_connector.clear_table('test_table', 'id')
    count = db_connector.count_table('test_table')
    assert count == 0


def test_push_table(db_connector):
    # Clear the table before pushing new data
    db_connector.clear_table('test_table', 'id')
    data = {'name': ['test4', 'test5'], 'value': [400, 500]}
    df = pd.DataFrame(data)
    db_connector.push_table(df, 'test_table', 'id')
    count = db_connector.count_table('test_table')
    assert count == 2


def test_cache_table_counts(db_connector):
    db_connector.cache_table_counts()
    cached_count = db_connector.get_cached_table_count('test_table')
    actual_count = db_connector.count_table('test_table')
    assert cached_count == actual_count


def test_log_table_stats(db_connector, caplog):
    # Ensure cache is populated
    db_connector.cache_table_counts()
    # Configure caplog to capture logs at INFO level
    caplog.set_level(logging.INFO)
    # Log table stats
    db_connector.log_table_stats()
    # Verify that the logs contain the expected messages
    assert any("Table test_table has" in record.message for record in caplog.records)


def test_clear_db(db_connector):
    DatabasePostgres.TABLE_DATA = [{'name': 'test_table', 'id_col': 'id'}]
    data = {'id': [6, 7], 'name': ['test6', 'test7'], 'value': [600, 700]}
    df = pd.DataFrame(data)
    db_connector.push_table(df, 'test_table', 'id')
    db_connector.clear_db()
    count = db_connector.count_table('test_table')
    assert count == 0


def test_push_db(db_connector):
    DatabasePostgres.TABLE_DATA = [{'name': 'test_table', 'id_col': 'id'}]
    update_dict = {
        'test_table': pd.DataFrame({'name': ['test8', 'test9'], 'value': [800, 900]})
    }
    db_connector.push_db(update_dict)
    count = db_connector.count_table('test_table')
    assert count == 2


def test_get_id_col(db_connector):
    table_name = 'test_table'
    DatabasePostgres.TABLE_DATA = [{'name': 'test_table', 'id_col': 'id'}]
    id_col = DatabasePostgres.get_id_col(table_name)
    assert id_col == 'id'


def test_context_manager():
    with DatabasePostgres(Config.SQLALCHEMY_DATABASE_URI) as db_connector:
        assert db_connector.connector is not None
        assert db_connector.cursor is not None
    assert db_connector.connector is None
    assert db_connector.cursor is None
