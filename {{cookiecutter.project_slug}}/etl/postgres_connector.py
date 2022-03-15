import os
import time
import logging
import psycopg2
import sqlalchemy
from flask import jsonify
import pandas as pd
import pandas_gbq
from google.cloud import secretmanager


class Config:
    def __init__(self):
        self.PROJECT_ID = os.environ.get('PROJECT_ID')
        self.APP_ID = os.environ.get('APP_ID', os.environ.get('SECRET_ID'))
        self.SECRET_ID = os.environ.get('SECRET_ID')


global_config = Config()
logger = logging.getLogger('frontend')
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)


def load_secrets(version_id='latest'):
    """
    Load secrets from Google Secrets Manager
    Access the payload for the given secret version if one exists. The version
    can be a version number as a string (e.g. "5") or an alias (e.g. "latest").
    """
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()
    # Build the resource name of the secret version.
    name = f"projects/{global_config.PROJECT_ID}/secrets/{global_config.APP_ID}/versions/{version_id}"
    # Access the secret version.
    response = client.access_secret_version(request={"name": name})
    # Parse the secret payload. Should be one key=val pair per line
    payload = response.payload.data.decode("UTF-8")
    secrets = {line.split('=')[0]: line.split('=')[1] for line in payload.split('\n')}
    return secrets


class BigQueryConnector:
    def __init__(self, project_id=None, app_id=None, bq_destination='lake'):
        self.project_id = project_id or global_config.PROJECT_ID
        secrets = load_secrets()
        self.bq_dataset = f"{secrets['OUT_BQ_DATASET']}_{bq_destination}"

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


class PostgresConnector:
    def __init__(self, db_url, eager_commit=True):
        self.db_url = db_url
        self.connector = None
        self.cursor = None
        self.engine = None
        self.eager_commit = eager_commit

    def start(self):
        # Obtain a database connection
        # Obtain a database cursor
        if self.connector is None or self.cursor is None:
            self.connector = psycopg2.connect(self.db_url)
            self.cursor = self.connector.cursor()
            self.engine = sqlalchemy.create_engine(self.db_url)
        return self.cursor

    def stop(self):
        if self.connector is not None or self.cursor is not None:
            self.connector.commit()
            self.cursor.close()
            self.connector.close()
            self.engine.dispose()
            self.connector = None
            self.cursor = None
            self.engine = None

    def commit(self):
        self.connector.commit()

    def execute(self, statement):
        self.cursor.execute(statement)
        if self.eager_commit is True:
            self.commit()

    def rollback(self):
        self.connector.rollback()

    @staticmethod
    def get_table_data():
        """ Todo - decouple from db schema. """
        return [{'name': 'user', 'id_col': 'id'},
                {'name': 'survey', 'id_col': 'survey_id'},
                {'name': 'coupon', 'id_col': 'id'},
                {'name': 'address', 'id_col': 'address_id'},
                {'name': 'order', 'id_col': 'order_id'},
                {'name': 'product', 'id_col': 'id'},
                {'name': 'email', 'id_col': 'id'},
                {'name': 'layout', 'id_col': 'id'},
                {'name': 'recipe', 'id_col': 'id'},
                {'name': 'event', 'id_col': 'id'},
                {'name': 'experiment', 'id_col': 'id'},
                {'name': 'contact', 'id_col': 'id'},
                {'name': 'mailinglist', 'id_col': 'id'},
                {'name': 'post', 'id_col': 'id'}]

    @staticmethod
    def get_id_col(table_name):
        table_data = PostgresConnector.get_table_data()
        for table in table_data:
            if table['name'] == table_name:
                return table['id_col']

    def get_table(self, table_name):
        return pd.read_sql_table(table_name, con=self.engine)

    def count_table(self, table_name):
        selectStatement = f'SELECT * FROM "{table_name}"'
        self.execute(selectStatement)
        return len(self.cursor.fetchall())

    @staticmethod
    def chunks(lst, n):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    def delete_by_ids(self, table_name, id_col_name, id_set, chunksize=100):
        start_time = time.time()
        order_chunks = list(self.chunks(list(id_set), chunksize))
        for chunk in order_chunks:
            self.execute(
                f'DELETE FROM "{table_name}" WHERE {id_col_name} in ({",".join([str(idx) for idx in chunk])});')
        print(f'{table_name} done! - {time.time() - start_time}')

    def clear_table(self, table_name, id_col):
        """
        Delete rows from a table without deleting the table
        """
        before_len = self.count_table(table_name)
        delete_statement = f'DELETE FROM "{table_name}" WHERE {id_col} > 0;'
        self.execute(delete_statement)
        print(f"Count of rows in table={table_name} from {before_len} to {self.count_table(table_name)}")

    def clear_db(self):
        """
        Delete rows from all tables without deleting the tables
        """
        # Iterate over the tables
        table_data = self.get_table_data()
        for table_cfg in table_data[::-1]:
            table_name = table_cfg['name']
            id_col = table_cfg['id_col']
            self.clear_table(table_name, id_col)

    def reset_max_id(self, table_name, id_col):
        set_max_id = f'SELECT setval(\'{table_name}_{id_col}_seq\', (SELECT MAX({id_col}) FROM "{table_name}")+1);'
        self.execute(set_max_id)

    def push_table(self, table_df, table_name, id_col):
        """
        Push a pandas dataframe into a compatible postgres db
        """
        dtype = {'data': sqlalchemy.types.JSON,
                 'responses': sqlalchemy.types.JSON,
                 'order_confirmation': sqlalchemy.types.JSON,
                 'config': sqlalchemy.types.JSON,
                 'attachments': sqlalchemy.types.JSON}
        dtype = {key: val for key, val in dtype.items() if key in table_df.columns}
        table_df.to_sql(table_name, con=self.engine, index=False, if_exists="append",
                        dtype=dtype, chunksize=10000, method='multi')
        self.reset_max_id(table_name, id_col)

    def push_db(self, update_dict):
        """
        Push a full dict of pandas dfs in order to overwrite a db with all new data
        :param update_dict: dict of pandas dfs to overwrite tables {'table_name': table_df, ...}
        """
        for table_name, table_df in update_dict.items():
            print(f'clearing {table_name}')
            self.clear_table(table_name, self.get_id_col(table_name))
        for table_name, table_df in reversed(list(update_dict.items())):
            print(f'migrating {table_name}')
            if table_df is not None:
                self.push_table(table_df, table_name, self.get_id_col(table_name))
        logger.debug('PostgresConnector.push_db() complete!')


class ProdFollower(PostgresConnector):
    """
    An auto-connecting bridge to the Prod Follower database.
    """

    def __init__(self, follower_name='engine-prod-follower'):
        if follower_name == 'engine-prod':
            raise ValueError('The production DB follower cannot be the production DB itself.')
        print('loading secrets...')
        secrets = load_secrets()
        self.in_db_url = secrets['DATABASE_URL']
        self.follower_db_url = secrets['OUT_DB_URL'].replace('{db}', follower_name)
        print(f'self.in_db_url={self.in_db_url.split("/")[-1]}  '
              f'self.follower_db_url={self.follower_db_url.split("/")[-1]}')
        super(ProdFollower, self).__init__(db_url=self.follower_db_url)

    def update(self, is_replace=False):
        """
        Make a copy of the DB at DATABASE_URL into the DB follower and then open a connection to it
        """
        # Upgrade the db
        os.environ['OUT_DB_URL'] = self.follower_db_url
        if is_replace is True:
            print('clearing follower_db...')
            self.clear_db()
        # Load all of the tables in reverse order to prevent ForeignKeyViolations
        table_data = self.get_table_data()
        table_dict = {}
        prod_connector = PostgresConnector(self.in_db_url)
        prod_connector.start()
        for table_cfg in list(reversed(table_data)):
            table_name = table_cfg['name']
            table_dict[table_name] = pd.read_sql_table(table_name, con=prod_connector.engine)
            print(f'loaded table {table_name} with {table_dict[table_name].shape[0]} rows...')
        prod_connector.stop()
        # Load each table and migrate it
        for table_cfg in table_data:
            table_name = table_cfg['name']
            id_col = table_cfg['id_col']
            # Get the ids that already exist in the out db and drop them.
            table_df = table_dict[table_name]
            current_ids = set(self.get_table(table_name)[id_col].tolist())
            print(
                f"migrating table: {table_name} of len={table_df.shape[0]} with {table_df.shape[0] - len(current_ids)} new items")
            table_df = table_df.loc[table_df[id_col].apply(lambda x: x not in current_ids), :]
            # If any data remains, sync it into the remote table
            if table_df.shape[0] > 0:
                table_df.to_sql(table_name, con=self.engine, index=False, if_exists="append",
                                dtype={'data': sqlalchemy.types.JSON,
                                       'responses': sqlalchemy.types.JSON,
                                       'order_confirmation': sqlalchemy.types.JSON,
                                       'config': sqlalchemy.types.JSON,
                                       'attachments': sqlalchemy.types.JSON})
                self.reset_max_id(table_name, id_col)
        self.connector.commit()


def filter_by_days(df, num_days):
    if 'updated' in df.columns:
        return df.loc[df['updated'] > pd.Timestamp.now() - pd.Timedelta(days=num_days), :]
    else:
        return df.loc[df['last_updated'] > pd.Timestamp.now() - pd.Timedelta(days=num_days), :]


def prep_for_analysis(func):
    """
    Decorator to prep a table for analysis. This is used in Data Warehouse transformations.
    A copy of the table is made and the date is filtered by the 'created' column which is universal across tables.
    """

    def wrapper_within_n_days(*args, **kwargs):
        target_df = args[0]
        num_days = kwargs.get('num_days', 90)
        if len(args) > 1:
            target_dfs = [filter_by_days(df, num_days) for df in args]
            return func(*target_dfs, num_days=num_days)
        else:
            target_df = filter_by_days(target_df, num_days)
            return func(target_df, num_days)

    return wrapper_within_n_days


@prep_for_analysis
def get_customer_df(address_df, user_df, num_days=90):
    """
    Customers - people that have entered addresses and purchased products
    """
    customer_df = pd.merge(address_df, user_df, how='inner',
                           left_on='user_id', right_on='id', suffixes=('_address', '_user'))
    return customer_df


@prep_for_analysis
def get_prints_df(customer_df, product_df, num_days=90):
    """
    Prints - All product data for Customers used to render their book.
    """
    # Get characters and renders for all products.
    # Customers may be repeated because Prints-to-Customer is many-to-one
    prints_df = pd.merge(customer_df, product_df, how='right', on='user_id', suffixes=(None, '_product'))
    prints_df = prints_df.dropna(subset=['address_id'])
    # Fix up any column name conflicts
    prints_df = prints_df.rename(columns={'data_product': 'product_data', 'id_product': 'product_id'})
    # Unpack the product data
    prints_df['product_data_version'] = prints_df['product_data'].apply(lambda x: x.get('version', '0.2.3'))
    prints_df['product_data'] = prints_df['product_data'].apply(lambda x: x.get('data', {}))
    # Filter out incomplete products
    prints_df['is_complete'] = prints_df['product_data'].apply(lambda x: x.get('is_complete', None))
    # prints_df = prints_df.dropna(subset=['is_complete'])
    return prints_df


@prep_for_analysis
def get_renders_df(product_df, order_df, user_df, address_df, num_days=90):
    """
    Renders - All requested renders from order, both customer and tester
    """
    renders_df = pd.merge(product_df, order_df, how='left', on='order_id', suffixes=(None, '_order'))
    renders_df = pd.merge(renders_df, user_df, how='left', left_on='user_id', right_on='id', suffixes=(None, '_user'))
    renders_df = pd.merge(renders_df, address_df, how='left', on='user_id', suffixes=(None, '_address'))
    renders_df = renders_df.rename(columns={'data_product': 'data', 'timestamp_product': 'timestamp'})
    renders_df = renders_df[renders_df['is_in_cart'] == True]
    renders_df = renders_df.dropna(subset=['state'])
    renders_df['product_data'] = renders_df['data'].apply(lambda x: x.get('data', {}))
    return renders_df


@prep_for_analysis
def get_nav_df(survey_df, num_days=90):
    """
    Navigation - nav data from Survey data model refined into customer behavior
    """
    bot_names = ('python-requests', 'ahc', 'scrapy', 'catexplorador', 'google', 'go http', 'cfnetwork', 'ogscrper',
                 'go-http-client', 'masscan', 'nmap', 'curl', 'wget', 'libfetch', 'aiohttp', 'urllib', 'fasthttp',
                 'bot', 'googlestackdrivermonitoring', 'twitterbot', 'facebookexternal', 'bing', 'panscient.com',
                 'crawler', 'domtestcontaineragent', 'facebookexternalhit', 'semrush', 'webtech', 'axios')
    nav_df = survey_df.loc[~survey_df['data'].isna()].copy()
    # Break out metadata
    nav_df['entrypoint'] = nav_df['data'].apply(lambda x: x.get('data', {}).get('nav.entrypoint'))
    nav_df['nav_sequence'] = nav_df['data'].apply(lambda x: x.get('data', {}).get('nav.sequence', []))
    nav_df['user_agent'] = nav_df['data'].apply(lambda x: x.get('data', {}).get('meta.user_agent'))
    nav_df['browser'] = nav_df['data'].apply(lambda x: x.get('data', {}).get('meta.browser'))
    nav_df['platform'] = nav_df['data'].apply(lambda x: x.get('data', {}).get('meta.platform'))
    nav_df = nav_df[~nav_df['entrypoint'].isna()]
    nav_df = nav_df[~(nav_df['user_agent'] == '')]
    # Screen for missed bots. They should not appear in the Survey dataset
    nav_df['is_bot'] = nav_df['user_agent'].apply(lambda x: any([val in x.lower() for val in bot_names]))
    nav_df['is_bot'] = nav_df['is_bot'] | nav_df['entrypoint'].isin(['/wp-login.php', '/robots.txt'])
    bots_df = nav_df[nav_df['is_bot']]
    nav_df = nav_df[~nav_df['is_bot']]
    # Break out data on the User's navigation sequence
    nav_df['nav_depth'] = nav_df['nav_sequence'].apply(lambda x: len(set(x)))
    nav_df['is_bounce'] = nav_df['nav_depth'] < 2
    nav_df['nav_sequence_str'] = nav_df['nav_sequence'].apply(lambda x: ','.join(x))
    for event in ('blog', 'prompt', 'store', 'customize', 'stripe', 'confirm', 'print',
                  'planner', 'journal', 'notebook', 'trainer', 'muse'):
        nav_df[f'nav_seq_{event}'] = nav_df['nav_sequence_str'].apply(lambda x: event in x)
    # Tag Ads for further exploration in more specific tables
    nav_df['is_ad'] = nav_df['data'].apply(lambda x: x.get('data', {}).get('adgroupid')).isna() == False
    return nav_df


@prep_for_analysis
def get_device_df(nav_df, num_days=90):
    """
    Device - Usage and success rates of different devices
     * time windowed - look at the last 1, 7, 14, 28, and 90 days. Look for major changes in 1-7 and 7-28
    """
    devices = nav_df.groupby('platform')
    device_df = devices.mean()
    device_df['num_users'] = devices.count()['user']
    device_df['nav_depth_var'] = devices.var().get('nav_depth')
    device_df = device_df.sort_values('num_users', ascending=False)
    device_df = device_df.drop(columns=['survey_id', 'user', 'is_bot'])
    device_df = device_df.loc[device_df['num_users'] > 10]
    device_df.reset_index(level=0, inplace=True)
    return device_df


@prep_for_analysis
def get_ads_df(nav_df, num_days=90):
    """
    Ads - Subset of Nav delivered by ads and tagged with ads metadata.
    """
    ad_group_ids = {
        124842868958: "HabitTracker",
        124842868998: "Journal",
        124842869038: "Printable",
        124842869198: "Planner",
        124842869238: "Notebook",
        124842869278: "Prompts",
        124842869438: "Muse",
        124842869478: "Trainer",
        112406733747: "Remarketing",
        107743607163: "Journaling",
        107743607203: "Self-Love",
        107743607243: "Planner",
        107743607403: "BuildConfidence",
        107743607443: "CreativePrompts",
        107743607483: "StressManagement",
        107743607643: "HealthyLifestyle",
        115894500929: "Ad group 1",
        0: "unknown"
    }
    ads_df = nav_df.loc[nav_df['is_ad'] == True, :]
    ads_df.loc[:, 'src'] = ads_df['data'].apply(lambda x: x.get('data').get('src'))
    ads_df.loc[:, 'campaignid'] = ads_df['data'].apply(lambda x: x.get('data').get('campaignid'))
    ads_df.loc[:, 'adgroupid'] = ads_df['data'].apply(lambda x: x.get('data').get('adgroupid', '0'))
    ads_df.loc[:, 'adgroup'] = ads_df['adgroupid'].apply(lambda x: ad_group_ids[int(x or 0)])
    ads_df.loc[:, 'creative'] = ads_df['data'].apply(lambda x: x.get('data').get('creative'))
    ads_df.loc[:, 'keyword'] = ads_df['data'].apply(lambda x: x.get('data').get('keyword'))
    ads_df.loc[:, 'persona'] = ads_df['data'].apply(lambda x: x.get('data').get('nav.landing_persona'))
    return ads_df


@prep_for_analysis
def get_adgroup_df(ads_df, num_days=90):
    """
    Adgroups - Look at the effectiveness of different ad groups in bounce and close rate.
     * time windowed - look at the last 1, 7, 14, 28, and 90 days. Look for major changes in 1-7 and 7-28
    """
    adgroups = ads_df.groupby('adgroup')
    adgroup_df = adgroups.mean()
    adgroup_df['num_users'] = adgroups.count()['user']
    adgroup_df['nav_depth_var'] = adgroups.var().get('nav_depth')
    adgroup_df = adgroup_df.sort_values('num_users', ascending=False)
    adgroup_df = adgroup_df.drop(columns=['survey_id', 'user', 'is_bot'])
    adgroup_df = adgroup_df.loc[adgroup_df['num_users'] > 10]
    adgroup_df.reset_index(level=0, inplace=True)
    return adgroup_df


def push_to_lake(event, context):
    """
    Push a batch of data to the data lake
    """
    logger.info("loading secrets")
    secrets = load_secrets()
    logger.info("secrets loaded")
    table_data = [{'name': 'user', 'id_col': 'id'},
                  {'name': 'email', 'id_col': 'id'},
                  {'name': 'layout', 'id_col': 'id'},
                  {'name': 'product', 'id_col': 'id'},
                  {'name': 'experiment', 'id_col': 'id'},
                  {'name': 'recipe', 'id_col': 'id'},
                  {'name': 'event', 'id_col': 'id'},
                  {'name': 'address', 'id_col': 'address_id'},
                  {'name': 'contact', 'id_col': 'id'},
                  {'name': 'mailinglist', 'id_col': 'id'},
                  {'name': 'survey', 'id_col': 'survey_id'},
                  {'name': 'coupon', 'id_col': 'id'},
                  {'name': 'order', 'id_col': 'order_id'},
                  {'name': 'post', 'id_col': 'id'}]
    for table_cfg in table_data:
        table = table_cfg['name']
        logger.info(f"processing table {table}")
        bq_table = f"{secrets['OUT_BQ_DATASET']}_lake.{table}"
        id_col = table_cfg['id_col']
        bq = BigQueryConnector()
        try:
            table_df = pd.read_sql_table(table, secrets['DATABASE_URL'])
            if table == "user":
                table_df = table_df.drop(columns="password_hash")
            # Sort by timestamp if the option is available
            if "timestamp" in list(table_df.columns):
                table_df = table_df.sort_values(by=["timestamp"], ascending=False)
            if table_df.shape[0] > 0:
                logger.info(f"migrating table: {table}")
                bq.update_table(table_df=table_df, bq_table_name=bq_table, id_col_name=id_col)
        except ValueError as err:
            logger.warning(f"ValueError: {err}")


def push_to_warehouse(event, context):
    logger.info('downloading tables...')
    pf = ProdFollower()
    pf.start()
    pf.update(is_replace=False)
    product_df = pf.get_table('product')
    survey_df = pf.get_table('survey')
    order_df = pf.get_table('order')
    user_df = pf.get_table('user')
    address_df = pf.get_table('address')
    # Hook into BigQuery and prep for uploads. Upload tables for ranges of 1, 7, 14, 28, and 90 days before today.
    gbq = BigQueryConnector(bq_destination='warehouse')
    logger.info('pushing to gbq...')
    for time_span in (1, 3, 7, 14, 28, 90):
        customer_df = get_customer_df(address_df, user_df, num_days=time_span)
        prints_df = get_prints_df(customer_df, product_df, num_days=time_span)
        renders_df = get_renders_df(product_df, order_df, user_df, address_df, num_days=time_span)
        nav_df = get_nav_df(survey_df, num_days=time_span)
        device_df = get_device_df(nav_df, num_days=time_span)
        ads_df = get_ads_df(nav_df, num_days=time_span)
        adgroup_df = get_adgroup_df(ads_df, num_days=time_span)
        dw_tables = [
            {'name': 'customer_df', 'df': customer_df},
            {'name': 'prints_df', 'df': prints_df},
            {'name': 'nav_df', 'df': nav_df},
            {'name': 'device_df', 'df': device_df},
            {'name': 'ads_df', 'df': ads_df},
            {'name': 'adgroup_df', 'df': adgroup_df},
            {'name': 'renders_df', 'df': renders_df}
        ]
        for table_dict in dw_tables:
            logger.info(
                f"Replacing table {table_dict['name']}-{time_span} of len({table_dict['df'].shape[0]}) and memory_usage=={table_dict['df'].memory_usage().sum() / 1000000} MB")
            gbq.replace_table(bq_table_name=f"{table_dict['name']}-{time_span}", table_df=table_dict['df'])
    print("Done!")


def get_new_renders(request):
    """
    Get renders for purchases or demos that need to be printed
    """
    request_json = request.get_json(silent=True)
    # Ensure that the request UID matches the secret
    secrets = load_secrets()
    if secrets['DOWNLOADER_UID'] != request_json.get('DOWNLOADER_UID'):
        return jsonify({'success': False, 'message': 'Error: invalid DOWNLOADER_UID'})
    num_days = request_json.get('num_days', 60)
    logger.info('downloading tables...')
    pf = ProdFollower()
    pf.start()
    pf.update(is_replace=False)
    product_df = pf.get_table('product')
    order_df = pf.get_table('order')
    user_df = pf.get_table('user')
    address_df = pf.get_table('address')
    logger.info('gathering render data...')
    renders_df = get_renders_df(product_df, order_df, user_df, address_df, num_days=num_days)
    # Export the bulk data to json
    out_json = renders_df.convert_df_to_json(orient='records', date_format='epoch', date_unit='s', indent=4)
    return out_json
