"""

Adapters - interfaces to 3rd-party services

Alert - Send alerts over slack, zapier, email, and/or logging.
Email - Send emails by modifying templates with params
Storage - Upload and download blobs from cloud storage

Each represent abstract access to whatever services are specified in the global_config.
Therefore, the adapter system is flexible, dynamic, and configurable.

While we did attempt to simplify dependencies by only loading the services specified by using importlib,
we opted against that added complexity since we'd still need to import all to run unit and integration tests.

"""