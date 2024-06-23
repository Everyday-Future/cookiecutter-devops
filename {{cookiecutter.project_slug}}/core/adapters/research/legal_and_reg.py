


"""

ProPublica API

https://www.propublica.org/datastore/apis

"""
from config import Config


class ProPublicaAPI:
    """
    Interface to Congress, voting, and other public documents
    NOTE - replace congress API with https://api.congress.gov/ since propublica is shutting theirs down.
    """
    @classmethod
    def search_congress_api(cls):
        raise NotImplementedError("TODO")

    @classmethod
    def search_campaign_finance_api(cls):
        raise NotImplementedError("TODO")

    @classmethod
    def search_nonprofit_api(cls):
        raise NotImplementedError("TODO")


"""

Court Listener

https://www.courtlistener.com/help/api/bulk-data/

"""


class CourtListenerAPI:
    """
    Interface to court documents, disclosures, and rulings
    """


"""

Harvard Case Law API

https://case.law/docs/site_features/api

"""


class HarvardCaseLawAPI:
    """
    Interface to court documents, disclosures, and rulings
    """


"""

OpenFDA

https://open.fda.gov/apis/try-the-api/

"""


class OpenFDAAPI:
    """
    Interface to OpenFDA
    """











