import time
import pytest
from datetime import datetime, timedelta, timezone
from core.adapters.research.news import MediastackAPI, TheNewsAPI, NewsAPIorgAPI


@pytest.fixture(scope="function")
def mediastack_api():
    return MediastackAPI()


@pytest.fixture(scope="function")
def thenews_api():
    return TheNewsAPI()


@pytest.fixture(scope="function")
def newsapi_org_api():
    return NewsAPIorgAPI()


# Sources


def test_mediastack_get_sources(mediastack_api):
    sources = mediastack_api.get_sources()
    assert sources is not None
    print('sources', sources)
    assert "data" in sources


def test_thenewsapi_get_sources(thenews_api):
    sources = thenews_api.get_sources()
    assert sources is not None
    print('sources', sources)
    assert "data" in sources


@pytest.mark.skip('Unauthorized for free plan')
def test_newsapiorg_get_sources(newsapi_org_api):
    sources = newsapi_org_api.get_sources()
    assert sources is not None
    print('sources', sources)
    assert "sources" in sources


# Live Articles


def test_mediastack_get_live_articles(mediastack_api):
    articles = mediastack_api.get_live_articles()
    assert articles is not None
    print('articles', articles)
    assert "data" in articles
    # Test article formatting
    articles = mediastack_api.format_articles(articles)
    print('articles', articles)
    assert len(articles) > 0


def test_thenewsapi_get_live_articles(thenews_api):
    articles = thenews_api.get_live_articles()
    assert articles is not None
    print('articles', articles)
    assert "data" in articles
    # Test article formatting
    articles = thenews_api.format_articles(articles)
    print('articles', articles)
    assert len(articles) > 0


@pytest.mark.skip('keep limited for free plan')
def test_newsapiorg_get_live_articles(newsapi_org_api):
    articles = newsapi_org_api.get_live_articles()
    assert articles is not None
    print('articles', articles)
    assert "articles" in articles
    # Test article formatting
    articles = newsapi_org_api.format_articles(articles)
    print('articles', articles)
    assert len(articles) > 0


# Historical Articles


def test_mediastack_get_historical_articles(mediastack_api):
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()
    articles = mediastack_api.get_historical_articles(start_date=start_date, end_date=end_date)
    assert articles is not None
    print('articles', articles)
    assert "data" in articles


def test_thenewsapi_get_historical_articles(thenews_api):
    start_date = datetime.now().replace(tzinfo=timezone.utc) - timedelta(days=7)
    articles = thenews_api.get_historical_articles(start_date=start_date)
    assert articles is not None
    print('articles', articles)
    assert "data" in articles
    # Reset the throttle and try the same operation with .update()
    time.sleep(3.0)
    thenews_api.last_updated = 0
    articles = thenews_api.update(start_date=start_date)
    assert len(articles) > 0


@pytest.mark.skip('keep limited for free plan')
def test_newsapiorg_get_historical_articles(newsapi_org_api):
    start_date = datetime.now() - timedelta(days=7)
    articles = newsapi_org_api.get_historical_articles(start_date=start_date)
    assert articles is not None
    print('articles', articles)
    assert "articles" in articles


def test_news_api_base_throttling(thenews_api):
    thenews_api.max_freq_s = 1
    assert thenews_api.is_throttled() is False
    articles = thenews_api.get_live_articles()
    assert articles is not None
    assert thenews_api.is_throttled() is True
    time.sleep(1.2)
    assert thenews_api.is_throttled() is False


def test_news_api_base_is_unique_article(thenews_api):
    assert thenews_api.is_unique_article(article_hash='1234') is True
    assert thenews_api.is_unique_article(article_hash='1234') is False
    assert thenews_api.is_unique_article(article_hash='12345') is True
    assert thenews_api.is_unique_article(article_hash='1234') is False
    assert thenews_api.is_unique_article(article_hash='12345') is False

