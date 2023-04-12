import os
import time
import logging
import psycopg2
import sqlalchemy
from flask import jsonify
import pandas as pd
import pandas_gbq
# noinspection PyPackageRequirements
from google.cloud import secretmanager


logger = logging.getLogger('backend')
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class Config:
    def __init__(self):
        # Get the mounted secrets from the environment
        self.SECRETS = os.environ.get('SECRETS', '').split('\n')
        self.SECRETS = {secret.split('=')[0]: secret.split('=')[1] for secret in self.SECRETS}
        self.ENV = os.environ.get('ENV', 'staging')
        self.PROJECT_ID = os.environ.get('PROJECT_ID')
        self.APP_ID = os.environ.get('APP_ID', os.environ.get('SECRET_ID'))
        self.SECRET_ID = os.environ.get('SECRET_ID')
        # Conn str of the staging/prod db to be backed up
        self.OPERATIONAL_DB_URL = self.SECRETS.get('DATABASE_URL')
        # Conn str of the follower db, optionally with {db} as a placeholder for the database name itself.
        self.FOLLOWER_DB_URL = self.SECRETS.get('OUT_DB_URL')
        # The Lakehouse location in BigQuery
        self.BQ_DATASET = self.SECRETS.get('OUT_BQ_DATASET')
        self.OPERATIONAL_DB_TABLES = [
            {'name': 'user', 'id_col': 'id'},
            {'name': 'survey', 'id_col': 'id'},
            {'name': 'stats', 'id_col': 'id'},
            {'name': 'coupon', 'id_col': 'id'},
            {'name': 'address', 'id_col': 'id'},
            {'name': 'order', 'id_col': 'id'},
            {'name': 'cart', 'id_col': 'id'},
            {'name': 'product', 'id_col': 'id'},
            {'name': 'email', 'id_col': 'id'},
            {'name': 'event', 'id_col': 'id'},
            {'name': 'experiment', 'id_col': 'id'},
            {'name': 'contact', 'id_col': 'id'},
            {'name': 'mailinglist', 'id_col': 'id'},
            {'name': 'post', 'id_col': 'id'}
        ]
        # Manually load the secrets if they couldn't be found in the environment
        if any([obj is None for obj in (self.OPERATIONAL_DB_URL, self.FOLLOWER_DB_URL, self.BQ_DATASET)]):
            if self.PROJECT_ID is not None and self.SECRET_ID is not None:
                print('no secrets found in environment. Loading manually...')
                self.load_secrets()

    def load_secrets(self, version_id='latest'):
        """
        Load secrets from Google Secrets Manager
        Access the payload for the given secret version if one exists. The version
        can be a version number as a string (e.g. "5") or an alias (e.g. "latest").
        """
        # Build the resource name of the secret version.
        name = f"projects/{self.PROJECT_ID}/secrets/{self.APP_ID}/versions/{version_id}"
        print(f'loading secrets from {name}')
        # Create the Secret Manager client.
        client = secretmanager.SecretManagerServiceClient()
        # Access the secret version.
        response = client.access_secret_version(request={"name": name})
        # Parse the secret payload. Should be one key=val pair per line
        payload = response.payload.data.decode("UTF-8")
        secrets = {line.split('=')[0]: line.split('=')[1] for line in payload.split('\n') if '=' in line}
        self.OPERATIONAL_DB_URL = secrets.get('DATABASE_URL')
        self.FOLLOWER_DB_URL = secrets.get('OUT_DB_URL')
        self.BQ_DATASET = secrets.get('OUT_BQ_DATASET')
        print(f'secrets loaded: self.OPERATIONAL_DB_URL={self.OPERATIONAL_DB_URL is not None} '
              f'self.FOLLOWER_DB_URL={self.FOLLOWER_DB_URL is not None} self.BQ_DATASET={self.BQ_DATASET is not None}')
        return secrets


class BigQueryConnector:
    def __init__(self, cfg: Config):
        self.project_id = cfg.PROJECT_ID
        self.bq_dataset = f"{cfg.BQ_DATASET}-{cfg.ENV}"

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
                              project_id=self.project_id,
                              if_exists="append")


def push_to_lake():
    """
    Push a batch of data to the data lake
    """
    logger.info("loading Config")
    cfg = Config()
    logger.info(f"Config loaded = {cfg.OPERATIONAL_DB_URL is not None}")
    time.sleep(0.5)
    for table_cfg in cfg.OPERATIONAL_DB_TABLES:
        table = table_cfg['name']
        logger.info(f"processing table {table}")
        bq_table = f"{cfg.BQ_DATASET}_{cfg.ENV}.{table}"
        id_col = table_cfg['id_col']
        bq = BigQueryConnector(cfg=cfg)
        try:
            table_df = pd.read_sql_table(table, cfg.OPERATIONAL_DB_URL)
            # Sort by timestamp if the option is available
            if "updated_at" in list(table_df.columns):
                table_df = table_df.sort_values(by=["updated_at"], ascending=False)
            if table_df.shape[0] > 0:
                logger.info(f"migrating table: {table}")
                bq.update_table(table_df=table_df, bq_table_name=bq_table, id_col_name=id_col)
        except ValueError as err:
            logger.warning(f"ValueError: {err}")


def run(*args, **kwargs):
    push_to_lake()
    return jsonify({'success': True})
