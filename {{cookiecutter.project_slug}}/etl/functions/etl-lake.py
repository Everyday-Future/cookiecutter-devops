# Import all of the basic postgres and gbq operations.
import etl

global_config = etl.Config()


def push_to_warehouse(event, context):
    etl.push_to_lake(event, context)
