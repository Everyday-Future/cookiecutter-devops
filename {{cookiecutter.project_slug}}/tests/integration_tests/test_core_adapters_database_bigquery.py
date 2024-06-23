import os
import pytest
import pandas as pd
# noinspection PyPackageRequirements
from google.oauth2 import service_account
from core.adapters.database.bigquery import BigQueryConnector


@pytest.fixture(scope='module')
def connector():
    project_id = os.getenv('GCP_PROJECT_ID')
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    lake = os.getenv('BQ_LAKE')
    save_dir = os.getenv('SAVE_DIR')

    credentials = service_account.Credentials.from_service_account_file(creds_path)
    return BigQueryConnector(project_id=project_id, creds_path=creds_path, lake=lake, save_dir=save_dir,
                             credentials=credentials)


@pytest.fixture
def test_data():
    return pd.DataFrame({
        'id': [1, 2, 3],
        'data': ['{"key1": "value1"}', '{"key2": "value2"}', '{"key3": "value3"}']
    })


def test_query_table_by_id(connector):
    df = connector.query_table_by_id(1, 'test_table')
    assert not df.empty
    assert 'id' in df.columns
    assert 'data' in df.columns


def test_save_result_df_to_json(connector, test_data):
    filename = 'test_result.json'
    result_file = connector.save_result_df_to_json(test_data, filename)
    assert os.path.exists(result_file)
    with open(result_file) as f:
        data = f.read()
    assert '"key1": "value1"' in data
    os.remove(result_file)


def test_replace_table(connector, test_data):
    connector.replace_table('test_table', test_data)
    df = connector.query_table_by_id(1, 'test_table')
    assert not df.empty


def test_update_table(connector, test_data):
    # Initial replace to ensure the table exists
    connector.replace_table('test_table', test_data)

    # Create new data with an existing and a new ID
    new_data = pd.DataFrame({
        'id': [3, 4],
        'data': ['{"key3": "new_value3"}', '{"key4": "value4"}']
    })
    connector.update_table('test_table', 'id', new_data)

    df = connector.query_table_by_id(3, 'test_table')
    assert df.loc[df['id'] == 3, 'data'].values[0] == '{"key3": "new_value3"}'
    df = connector.query_table_by_id(4, 'test_table')
    assert not df.empty


def test_handle_schema_changes(connector):
    new_schema = {'id': 'INT64', 'data': 'STRING', 'new_column': 'STRING'}
    connector.handle_schema_changes('test_table', new_schema)
    schema = connector.get_table_schema('test_table')
    assert 'new_column' in schema


def test_get_table_schema(connector):
    schema = connector.get_table_schema('test_table')
    assert isinstance(schema, dict)
    assert 'id' in schema
    assert 'data' in schema


def test_update_table_schema(connector):
    new_schema = {'id': 'INT64', 'data': 'STRING', 'extra_column': 'STRING'}
    connector.update_table_schema('test_table', new_schema)
    schema = connector.get_table_schema('test_table')
    assert 'extra_column' in schema
