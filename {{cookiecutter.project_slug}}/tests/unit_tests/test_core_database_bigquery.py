import json
import os.path

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from config import Config
from core.adapters.database.bigquery import BigQueryConnector


@pytest.fixture
def connector():
    with patch('core.adapters.database.bigquery.service_account.Credentials.from_service_account_file') as mock_creds:
        mock_creds.return_value = MagicMock()
        return BigQueryConnector()


def test_query_table_by_id(connector):
    with patch('core.adapters.database.bigquery.pandas_gbq.read_gbq') as mock_read_gbq:
        mock_read_gbq.return_value = pd.DataFrame({'id': [1], 'data': ['{"key": "value"}']})
        result = connector.query_table_by_id(1, 'test_table')
        assert not result.empty
        mock_read_gbq.assert_called_once_with("SELECT * FROM `lakehouse.test_table` WHERE id = 1")


def test_save_result_df_to_json():
    df = pd.DataFrame({'id': [1], 'data': ['{"key": "value"}']})
    fpath = os.path.join(Config.TEST_GALLERY_DIR, 'test_bq.json')
    filename = BigQueryConnector.save_result_df_to_json(df, fpath)
    assert filename == fpath
    with open(fpath) as f:
        data = json.load(f)
    assert data == [
        {
            "id": 1,
            "data": {"key": "value"}
        }
    ]


def test_replace_table(connector):
    df = pd.DataFrame({'id': [1], 'data': ['{"key": "value"}']})
    with patch('core.adapters.database.bigquery.pandas_gbq.to_gbq') as mock_to_gbq:
        connector.replace_table('test_table', df)
        mock_to_gbq.assert_called_once_with(df, destination_table='project_id.test_table', project_id='project_id',
                                            if_exists='replace')


def test_update_table(connector):
    df = pd.DataFrame({'id': [1, 2], 'data': ['{"key": "value"}', '{"key": "another_value"}']})
    existing_ids_df = pd.DataFrame({'id': [1]})

    with patch('core.adapters.database.bigquery.pandas_gbq.read_gbq') as mock_read_gbq, \
            patch('core.adapters.database.bigquery.pandas_gbq.to_gbq') as mock_to_gbq:
        mock_read_gbq.return_value = existing_ids_df
        connector.update_table('test_table', 'id', df)
        expected_df = df.loc[df['id'] != 1]
        assert expected_df.equals(mock_to_gbq.call_args[0][0])


def test_validate_query_parameters(connector):
    with pytest.raises(ValueError):
        connector.validate_query_parameters(-1, 'test_table')
    with pytest.raises(ValueError):
        connector.validate_query_parameters(1, '')


def test_handle_schema_changes(connector):
    new_schema = {'id': 'INT64', 'data': 'STRING'}
    existing_schema = {'id': 'INT64'}

    with patch.object(connector, 'get_table_schema', return_value=existing_schema), \
            patch.object(connector, 'update_table_schema') as mock_update_schema:
        connector.handle_schema_changes('test_table', new_schema)
        mock_update_schema.assert_called_once_with('project_id.test_table', new_schema)


def test_get_table_schema(connector):
    schema_df = pd.DataFrame({'column_name': ['id', 'data'], 'data_type': ['INT64', 'STRING']})
    with patch('core.adapters.database.bigquery.pandas_gbq.read_gbq', return_value=schema_df):
        schema = connector.get_table_schema('project_id.test_table')
        assert schema == {'id': 'INT64', 'data': 'STRING'}


def test_update_table_schema(connector):
    new_schema = {'id': 'INT64', 'data': 'STRING'}
    with patch('core.adapters.database.bigquery.pandas_gbq.read_gbq') as mock_read_gbq:
        connector.update_table_schema('project_id.test_table', new_schema)
        assert mock_read_gbq.call_count == 2
        mock_read_gbq.assert_any_call('ALTER TABLE `project_id.test_table` ADD COLUMN id INT64',
                                      project_id='project_id')
        mock_read_gbq.assert_any_call('ALTER TABLE `project_id.test_table` ADD COLUMN data STRING',
                                      project_id='project_id')
