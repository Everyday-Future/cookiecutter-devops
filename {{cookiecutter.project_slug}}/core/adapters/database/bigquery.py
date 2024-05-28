
import os
import ast
import pandas_gbq
from google.oauth2 import service_account
from api import global_config


class BigQueryConnector:
    def __init__(self, project_id=None, creds_path=None, lake=None, save_dir=None):
        self.project_id = project_id or global_config.PROJECT_ID
        # Load credentials
        creds_path = creds_path or os.path.join(global_config.CREDS_DIR, 'luminary-production_external-gbq.json')
        credentials = service_account.Credentials.from_service_account_file(creds_path)
        # Configure adapter and set credentials
        self.lake = lake or global_config.DATA_LAKEHOUSE_NAME
        self.save_dir = save_dir or global_config.TEST_GALLERY_DIR
        pandas_gbq.context.project = global_config.GCP_PRODUCT_ID
        pandas_gbq.context.credentials = credentials

    def query_table_by_id(self, idx: int, tablename: str):
        """
        Query any table by id
        :param idx: id
        :type idx: int
        :param tablename: lowercase name of the table to target
        :type tablename: str
        :return:
        :rtype:
        """
        return pandas_gbq.read_gbq(f"SELECT * FROM `{self.lake}.{tablename}` WHERE id = {idx}")

    @staticmethod
    def save_result_df_to_json(result_df, target_fname: str):
        """
        Transform the data column of a result_df into json data then save the resulting df to a json file
        :param result_df: dataframe returned from a query
        :type result_df: pd.DataFrame
        :param target_fname: file to save the resulting data to
        :type target_fname: str
        :return: filename of resulting file
        :rtype: str
        """
        if 'data' in result_df.columns:
            try:
                result_df['data'] = result_df['data'].apply(ast.literal_eval)
            except ValueError:
                pass
        result_df.to_json(target_fname, orient='records', indent=4)
        return target_fname

    def bq_table_loc(self, base_name):
        return f"{self.project_id}.{base_name}"

    def replace_table(self, bq_table_name, table_df):
        pandas_gbq.to_gbq(table_df,
                          destination_table=self.bq_table_loc(bq_table_name),
                          project_id=self.project_id,
                          if_exists="replace")

    def update_table(self, bq_table_name, id_col_name, table_df):
        """
        Get the current IDs already in the remote db and remove them from the local table.
        Then push an update to bigquery.
        """
        bq_table_loc = self.bq_table_loc(bq_table_name)
        sql = f"SELECT {id_col_name} FROM `{bq_table_loc}`"
        try:
            # Read the existing data from gbq
            gbq_df = pandas_gbq.read_gbq(sql, project_id=self.project_id)
            # Remove the existing ids from the current table
            current_ids = set(gbq_df[id_col_name].tolist())
            table_df = table_df.loc[table_df[id_col_name].apply(lambda x: x not in current_ids), :]
        except Exception as err:
            if 'not found in location' in str(err):
                pass  # the table doesn't exist in BQ and will be created
            else:
                raise
        # If any data remains, sync it into the remote table
        if table_df.shape[0] > 0:
            pandas_gbq.to_gbq(table_df, destination_table=bq_table_name,
                              project_id=global_config.PROJECT_ID,
                              if_exists="append")
