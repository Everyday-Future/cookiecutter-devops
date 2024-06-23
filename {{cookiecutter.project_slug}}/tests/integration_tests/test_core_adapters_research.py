
import os
import pytest
from datetime import date
from config import Config


# @pytest.mark.skip("Arxiv API Phase 1 complete")
def test_arxiv_api():
    from core.adapters.research.research import Arxiv
    results = Arxiv.get_search_results()
    print('results', results)
    assert results is not None


# @pytest.mark.skip("SerpAPI Phase 1 complete")
def test_serpapi_api():
    assert Config.SERPAPI_API_KEY is not None
    print('Config.SERPAPI_API_KEY', Config.SERPAPI_API_KEY)
    from core.adapters.research.background import SerpAPI
    trends = SerpAPI.get_google_trends('Coffee')
    print('trends', trends)
    assert trends is not None


@pytest.mark.skip
# @pytest.mark.skip("PubMed Phase 1 complete")
def test_pubmed_api():
    from core.adapters.research.research import PubMedClient
    print('trends', PubMedClient.search('Covid-19'))
    assert False


# @pytest.mark.skip("Reddit Phase 1 complete")
def test_reddit_api():
    assert Config.REDDIT_CLIENT_SECRET is not None
    print('Config.REDDIT_CLIENT_SECRET', Config.REDDIT_CLIENT_SECRET)
    from core.adapters.research.social import RedditAPI
    results = RedditAPI.search_subreddit('wallstreetbets')
    print('results', results)
    assert results is not None


# @pytest.mark.skip("Wikipedia Phase 1 complete")
def test_wikipedia_api():
    from core.adapters.research.background import WikipediaAPI
    summary = WikipediaAPI.get_summary('IBM (company)')
    print('IBM', summary)
    assert summary is not None


# @pytest.mark.skip("Semantic Scholar Phase 1 complete")
def test_semantic_scholar_api():
    assert Config.SEMANTIC_SCHOLAR_API_KEY is not None
    print('Config.SEMANTIC_SCHOLAR_API_KEY', Config.SEMANTIC_SCHOLAR_API_KEY)
    from core.adapters.research.research import SemanticScholarAPI
    results = SemanticScholarAPI.search_papers()
    print('results', results)
    assert results is not None


# @pytest.mark.skip("FRED API Phase 1 complete")
def test_fred_api():
    assert Config.FRED_API_KEY is not None
    print('Config.FRED_API_KEY', Config.FRED_API_KEY)
    from core.adapters.research.finance import FredAPI
    results = FredAPI.get_series()
    print('results', results)
    assert results is not None


# @pytest.mark.skip("Fact Check Tools API Phase 1 complete")
def test_fact_check_api():
    assert Config.FACT_CHECK_API_KEY is not None
    print('Config.FACT_CHECK_API_KEY', Config.FACT_CHECK_API_KEY)
    from core.adapters.research.background import GoogleFactCheckToolsAPI
    results = GoogleFactCheckToolsAPI.search_fact_check('covid-19')
    print('results', results)
    assert results is not None


@pytest.mark.skip
# @pytest.mark.skip("World Bank API Phase 1 complete")
def test_world_bank_api():
    from core.adapters.research.finance import WorldBankAPI
    results = WorldBankAPI.search('Coffee')
    print('results', results)
    assert False


@pytest.mark.skip
def test_core_papers_api():
    # assert Config.CORE_PAPERS_API_KEY is not None
    # print('Config.CORE_PAPERS_API_KEY', Config.CORE_PAPERS_API_KEY)
    # from core.adapters.apis.core_papers_api import CorePapersAPI
    # results = CorePapersAPI.search_articles('covid-19')
    # print('results', results)
    assert False


@pytest.mark.skip
def test_propublica_api():
    # assert Config.PROPUBLICA_API_KEY is not None
    # print('Config.PROPUBLICA_API_KEY', Config.PROPUBLICA_API_KEY)
    # from core.adapters.apis.propublica_api import ProPublicaAPI
    # results = ProPublicaAPI.search()
    # print('results', results)
    assert False


@pytest.mark.skip
def test_open_fda_api():
    assert False


@pytest.mark.skip
def test_court_listener_api():
    assert False


@pytest.mark.skip
def test_harvard_case_law_api():
    assert False
