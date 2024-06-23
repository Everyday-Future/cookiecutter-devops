import os
import ast
import pandas as pd
import pandas_gbq
import logging
from google.oauth2 import service_account
from typing import Optional
from config import Config


class BigQueryConnector:
    def __init__(self, project_id: Optional[str] = None, creds_path: Optional[str] = None,
                 lake: Optional[str] = None, save_dir: Optional[str] = None,
                 credentials: Optional[service_account.Credentials] = None):
        self.project_id = project_id or Config.CLOUD_PROJECT_ID
        self.creds_path = creds_path or os.path.join(Config.CREDS_DIR, 'luminary-production_external-gbq.json')
        self.lake = lake or Config.DATA_LAKEHOUSE_NAME
        self.save_dir = save_dir or Config.TEST_GALLERY_DIR
        self.credentials = credentials or service_account.Credentials.from_service_account_file(self.creds_path)
        pandas_gbq.context.project = Config.CLOUD_PROJECT_ID
        pandas_gbq.context.credentials = self.credentials
        self.logger = logging.getLogger(__name__)

    def query_table_by_id(self, idx: int, tablename: str) -> pd.DataFrame:
        self.validate_query_parameters(idx, tablename)
        query = f"SELECT * FROM `{self.lake}.{tablename}` WHERE id = {idx}"
        self.logger.debug(f"Running query: {query}")
        return pandas_gbq.read_gbq(query)

    @staticmethod
    def save_result_df_to_json(result_df: pd.DataFrame, target_fname: str) -> str:
        if 'data' in result_df.columns:
            try:
                result_df['data'] = result_df['data'].apply(ast.literal_eval)
            except ValueError as e:
                logging.error(f"Error parsing data column: {e}")
        result_df.to_json(target_fname, orient='records', indent=4)
        return target_fname

    def bq_table_loc(self, base_name: str) -> str:
        return f"{self.project_id}.{base_name}"

    def replace_table(self, bq_table_name: str, table_df: pd.DataFrame) -> None:
        self.logger.info(f"Replacing table {bq_table_name}")
        pandas_gbq.to_gbq(table_df, destination_table=self.bq_table_loc(bq_table_name),
                          project_id=self.project_id, if_exists="replace")

    def update_table(self, bq_table_name: str, id_col_name: str, table_df: pd.DataFrame) -> None:
        bq_table_loc = self.bq_table_loc(bq_table_name)
        sql = f"SELECT {id_col_name} FROM `{bq_table_loc}`"
        self.logger.debug(f"Running query: {sql}")
        try:
            gbq_df = pandas_gbq.read_gbq(sql, project_id=self.project_id)
            current_ids = set(gbq_df[id_col_name].tolist())
            table_df = table_df.loc[table_df[id_col_name].apply(lambda x: x not in current_ids), :]
        except Exception as err:
            if 'not found in location' in str(err):
                self.logger.warning(f"Table {bq_table_loc} not found in location, it will be created")
            else:
                raise
        if table_df.shape[0] > 0:
            self.logger.info(f"Updating table {bq_table_name} with new data")
            pandas_gbq.to_gbq(table_df, destination_table=bq_table_name,
                              project_id=Config.CLOUD_PROJECT_ID,
                              if_exists="append")

    def validate_query_parameters(self, idx: int, tablename: str) -> None:
        if not isinstance(idx, int) or idx < 0:
            raise ValueError("Index must be a non-negative integer")
        if not isinstance(tablename, str) or not tablename:
            raise ValueError("Table name must be a non-empty string")

    def handle_schema_changes(self, bq_table_name: str, new_schema: dict) -> None:
        """
        Handle schema changes for the BigQuery table by updating the schema to match new_schema.
        """
        bq_table_loc = self.bq_table_loc(bq_table_name)
        existing_schema = self.get_table_schema(bq_table_loc)
        if existing_schema != new_schema:
            self.logger.info(f"Updating schema for table {bq_table_name}")
            self.update_table_schema(bq_table_loc, new_schema)

    def get_table_schema(self, table_loc: str) -> dict:
        """
        Get the schema of a BigQuery table.
        """
        schema_query = f"SELECT column_name, data_type FROM `{table_loc}.INFORMATION_SCHEMA.COLUMNS`"
        schema_df = pandas_gbq.read_gbq(schema_query, project_id=self.project_id)
        schema_dict = dict(zip(schema_df['column_name'], schema_df['data_type']))
        return schema_dict

    def update_table_schema(self, table_loc: str, new_schema: dict) -> None:
        """
        Update the schema of a BigQuery table.
        """
        alter_queries = []
        for column, data_type in new_schema.items():
            alter_queries.append(f"ALTER TABLE `{table_loc}` ADD COLUMN {column} {data_type}")
        for query in alter_queries:
            self.logger.debug(f"Running schema update query: {query}")
            pandas_gbq.read_gbq(query, project_id=self.project_id)
