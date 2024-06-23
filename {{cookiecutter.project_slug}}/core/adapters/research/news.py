"""

News APIs
TheNewsAPI, Mediastack, NewsAPI.org

Collection of news event listeners with a standardized interface to the rest of the system.

"""
import math
import os
import re
import time
import hashlib
from enum import Enum
from collections import deque
from datetime import datetime, timedelta
from urllib.parse import urlparse
import pandas as pd
import requests
from requests.exceptions import RequestException
from config import Config
from core.adapters.parser import StringParser


class ArticleSource(Enum):
    MEDIASTACK = 'MEDIASTACK'
    THENEWSAPI = 'THENEWSAPI'
    NEWSAPIORG = 'NEWSAPIORG'


def deduplicate_list(items):
    """
    Deduplicates a list of dictionaries based on the 'native_id' key,
    keeping the item with the highest index for each unique 'native_id'.

    :param items: List of dictionaries with a 'native_id' key.
    :return: Deduplicated list of dictionaries.
    """
    seen = {}
    for item in reversed(items):
        if item['native_id'] not in seen:
            seen[item['native_id']] = item
    return list(seen.values())[::-1]


class NewsAPIBase:
    # Class-parameters to be overridden by subclass
    max_freq_s = 100
    base_url = 'https://newsapi.org/v2'

    def __init__(self, earliest_date: datetime = None, search_str: str = None,
                 categories: list = None, languages: list = None):
        self.session = requests.Session()
        self.last_updated = 0
        self.earliest_date = earliest_date or datetime.utcnow()
        # Define a class-level queue for de-duplicating articles. The size limit is arbitrary and can be adjusted.
        self.article_hashes = set()
        # Maintain insertion order for eviction when limits are reached.
        self.id_order = deque(maxlen=1000)
        self.hash_order = deque(maxlen=1000)
        # Query defaults
        self.search_str = search_str
        self.categories = categories
        self.languages = languages

    def __del__(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def is_throttled(self):
        """
        Throttle the API according to our current pricing plan
        """
        return (time.time() - self.last_updated) < self.max_freq_s

    def bump(self):
        """
        Reset the API throttling counter
        """
        self.last_updated = time.time()

    @staticmethod
    def clean_string(input_string):
        # Replace everything that is not a letter or number with an empty string
        cleaned_string = re.sub(r'[^a-zA-Z0-9]', '', input_string.lower())
        return cleaned_string

    @staticmethod
    def extract_domain(url):
        # Parse the URL to get the netloc part (domain and possible subdomain)
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        # Remove 'www.' if it exists
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain

    @staticmethod
    def hash_string_sha256(input_string):
        input_string = NewsAPIBase.clean_string(input_string)
        # Create a sha256 hash object
        hash_obj = hashlib.sha256()
        # Update the hash object with the bytes-like object (encode the string)
        hash_obj.update(input_string.encode())
        # Get the hexadecimal representation of the digest
        return hash_obj.hexdigest()

    def is_unique_article(self, article_hash):
        if article_hash in self.article_hashes:
            return False
        if len(self.hash_order) >= 1000:
            oldest_hash = self.hash_order.popleft()
            self.article_hashes.remove(oldest_hash)
        self.hash_order.append(article_hash)
        self.article_hashes.add(article_hash)
        return True

    def send_request(self, request_url, params):
        # Remove params that are unset to avoid API glitches
        params = {key: val for key, val in params.items() if val is not None}
        try:
            response = self.session.get(request_url, params=params, timeout=20)
            self.bump()
            response.raise_for_status()
            print('    request successful')
            return response.json()
            # return None
        except RequestException as e:
            print(f"Request failed: {e}")
            return None

    def format_articles(self, data: dict):
        """
        Parse the articles from the live data into the standard article format
        """
        raise NotImplementedError('NewsAPI child classes must implement their own data cleaning function')

    def get_sources(self, page=0, **kwargs):
        raise NotImplementedError('NewsAPI child classes must implement their own get_sources() function')

    def get_live_articles(self, page=0, **kwargs):
        raise NotImplementedError('NewsAPI child classes must implement their own get_live_news_articles() function')

    def get_historical_articles(self, start_date: datetime, end_date: datetime = None, page=0, **kwargs):
        raise NotImplementedError('NewsAPI child classes must implement their own get_historical_articles() function')

    def upload_articles(self, articles: list):
        """
        Get cleanly-formatted news data
        Wildcard filter unwanted keywords
        Dedupe each article against the in-memory queues
        Dedupe each article against the database
        Commit the articles to the DB
        Add the articles to the /Config.APP_NAME/news/raw MQTT feed to hand off to scrapers and decorators.
        After decoration, the message is dropped into /Config.APP_NAME/news/ingest for DeskRouter & CRAG
        """
        pass

    def update(self, search: str = None, categories: list = None, languages: list = None, start_date: datetime = None,
               end_date: datetime = None, page: int = 1, limit: int = None):
        """
        Page through the updated in the news packet, parse, and upload them
        """
        if self.is_throttled() is True:
            return None
        # Defaults for search patterns
        search = search or self.search_str
        categories = categories or self.categories
        languages = languages or self.languages
        # Search historical data if start_date specified
        if start_date is not None or end_date is not None:
            articles = self.get_historical_articles(search=search, categories=categories, languages=languages,
                                                    start_date=start_date, end_date=end_date,
                                                    page=page, limit=limit)
        else:
            articles = self.get_live_articles(search=search, categories=categories, languages=languages,
                                              page=page, limit=limit)
        if articles is None:
            print(f"warning - articles returned None")
            return None
        print(f'parsing {len(articles["data"] or [])} articles...')
        articles = self.format_articles(articles)
        unique_articles = []
        print(f'deduping {len(articles or [])} articles...')
        for article in articles:
            if self.is_unique_article(article['native_id']):
                unique_articles.append(article)
        print(f'deduping  {len(articles or [])} articles v2...')
        articles = deduplicate_list(unique_articles)
        print(f'upload  {len(articles or [])} articles...')
        return articles


class MediastackAPI(NewsAPIBase):
    """
    Interface to Mediastack - https://mediastack.com/documentation
    """
    base_url = 'https://api.mediastack.com/v1'
    last_updated = 0
    max_freq_s = 300

    def get_sources(self, page=0, **kwargs):
        """
        News Data Sources
        """
        params = {
            'access_key': Config.MEDIASTACK_API_KEY,
            'search': kwargs.get('search') or 'the',
            'categories': kwargs.get('categories') or '-sports,-entertainment',
            'languages': kwargs.get('languages') or 'en',
            'countries': kwargs.get('countries') or 'us',
            'offset': page * 100,
            'limit': 100,
        }
        return self.send_request(f'{MediastackAPI.base_url}/sources', params)

    def get_live_articles(self, page=0, **kwargs):
        """
        Live News Data
        """
        params = {
            'access_key': Config.MEDIASTACK_API_KEY,
            'keywords': kwargs.get('search'),
            'categories': kwargs.get('categories') or '-sports,-entertainment',
            'languages': kwargs.get('languages') or 'en',
            'countries': kwargs.get('countries') or 'us,-in',
            'sources': kwargs.get('sources') or '-americanbankingnews,-dvidshub,-etfdailynews,-thenationonlineng',
            'sort': kwargs.get('sort') or 'published_desc',
            'offset': page * 100,
            'limit': kwargs.get('limit') or 100,
        }
        return self.send_request(f'{MediastackAPI.base_url}/news', params)

    def get_historical_articles(self, start_date: datetime, end_date: datetime = None, page=0, **kwargs):
        """
        Search for news within a time period
        """
        date_str = start_date.strftime("%Y-%m-%d")
        if end_date is not None and end_date > start_date:
            end_date = end_date.strftime("%Y-%m-%d")
            date_str = f"{date_str},{end_date}"
        params = {
            'access_key': Config.MEDIASTACK_API_KEY,
            'date': date_str,
            'keywords': kwargs.get('search'),
            'categories': kwargs.get('categories') or '-sports,-entertainment',
            'languages': kwargs.get('languages') or 'en',
            'countries': kwargs.get('countries') or 'us,-in',
            'sources': kwargs.get('sources') or '-americanbankingnews,-dvidshub,-etfdailynews,-thenationonlineng',
            'sort': kwargs.get('sort') or 'published_desc',
            'offset': page * 100,
            'limit': kwargs.get('limit') or 100,
        }
        return self.send_request(f'{MediastackAPI.base_url}/news', params)

    @staticmethod
    def process_author(author_str):
        if author_str is None or NewsAPIBase.clean_string(author_str) == '':
            return 'unknown'
        else:
            return ','.join([art.strip() for art in author_str.lower().replace(' and ', ', ').split(',')])

    def format_articles(self, data: dict):
        """
        Parse the articles from the live data into the standard article format
        """
        if 'data' not in data:
            return None
        articles = data['data']
        formatted_articles = [
            {
                'native_id': NewsAPIBase.hash_string_sha256(article['title'] + article['description']),
                'adapter': 'MediastackAPI',
                'channel': NewsAPIBase.extract_domain(article['url']),
                'author': MediastackAPI.process_author(article.get('author')),
                'title': article['title'],
                'description': article['description'],
                'url': article['url'],
                'source': ','.join(article['source'].split(' | ')[0].split(' - ')[0].split(': ')[0].lower().strip()),
                'image_url': article['image'],
                'categories': article['category'].lower(),
                'language': article['language'],
                'country': article['country'],
                'published_at': datetime.fromisoformat(article['published_at'])
            } for article in articles
        ]
        return formatted_articles


class TheNewsAPI(NewsAPIBase):
    """
    Interface to Mediastack - https://mediastack.com/documentation
    """
    base_url = 'https://api.thenewsapi.com/v1'
    last_updated = 0
    max_freq_s = 15
    excl_domains = ('medium.com,dailyexcelsior.com,dawn.com,dnaindia.com,economictimes.indiatimes.com,'
                    'hardwarezone.com.sg,macrumors.com,freepressjournal.in,gurufocus.com,india.com,'
                    'indiatoday.in,ndtv.com,ndtvprofit.com,news.google.com,news18.com,news24.com,thehindu.com,'
                    'thesun.my,timesofindia.indiatimes.com,indiatimes.com,toronto.citynews.ca,winnipegfreepress.com')

    def get_sources(self, page=1, **kwargs):
        """
        News Data Sources
        https://www.thenewsapi.com/documentation
        """
        params = {
            'api_token': Config.THENEWSAPI_API_KEY,
            'categories': kwargs.get('categories') or 'general,science,business,health,tech,politics',
            'language': kwargs.get('languages') or 'en',
            'locale': kwargs.get('locale') or 'us',
            'limit': kwargs.get('limit') or 100,
            'page': kwargs.get('page') or page,
        }
        return self.send_request(f'{TheNewsAPI.base_url}/news/sources', params)

    def get_top_stories(self, page=1, **kwargs):
        """
        News Data Sources
        https://www.thenewsapi.com/documentation
        """
        params = {
            'api_token': Config.THENEWSAPI_API_KEY,
            'search': kwargs.get('search'),
            'categories': kwargs.get('categories') or 'general,science,business,health,tech,politics',
            'language': kwargs.get('languages') or 'en',
            'locale': kwargs.get('locale') or 'us',
            'limit': kwargs.get('limit') or 100,
            'page': kwargs.get('page') or page,
        }
        return self.send_request(f'{TheNewsAPI.base_url}/news/top', params)

    def get_live_articles(self, page=1, **kwargs):
        """
        News Data Sources
        https://www.thenewsapi.com/documentation
        """
        params = {
            'api_token': Config.THENEWSAPI_API_KEY,
            'search': kwargs.get('search'),
            'categories': kwargs.get('categories') or 'general,science,business,health,tech,politics',
            'exclude_categories': kwargs.get('exclude_categories') or 'entertainment,sports',
            'exclude_domains': kwargs.get('exclude_domains') or self.excl_domains,
            'language': kwargs.get('languages') or 'en',
            'locale': kwargs.get('locale') or 'us',
            'sort': 'published_at',
            'limit': kwargs.get('limit') or 100,
            'page': kwargs.get('page') or page,
        }
        return self.send_request(f'{TheNewsAPI.base_url}/news/all', params)

    def get_historical_articles(self, start_date: datetime, end_date: datetime = None, page=0, **kwargs):
        params = {
            'api_token': Config.THENEWSAPI_API_KEY,
            'search': kwargs.get('search'),
            'categories': kwargs.get('categories') or 'general,science,business,health,tech,politics',
            'exclude_categories': kwargs.get('exclude_categories') or 'entertainment,sports',
            'exclude_domains': kwargs.get('exclude_domains') or self.excl_domains,
            'language': kwargs.get('languages') or 'en',
            'locale': kwargs.get('locale') or 'us',
            'limit': kwargs.get('limit') or 100,
            'page': kwargs.get('page') or page,
        }
        if end_date is not None and end_date > start_date:
            params['published_after'] = start_date.strftime("%Y-%m-%d")
            params['published_before'] = end_date.strftime("%Y-%m-%d")
        else:
            params['published_on'] = start_date.strftime("%Y-%m-%d")
        return self.send_request(f'{TheNewsAPI.base_url}/news/all', params)

    def format_articles(self, data: dict):
        """
        Parse the articles from the live data into the standard article format
        """
        if 'data' not in data:
            return None
        articles = data['data']
        formatted_articles = [{
            'native_id': NewsAPIBase.hash_string_sha256(article['title'] + article['description']),
            'adapter': 'TheNewsAPI',
            'channel': NewsAPIBase.extract_domain(article['url']),
            'author': '',
            'title': article['title'],
            'description': article['description'],
            'body': article['snippet'],
            'url': article['url'],
            'source': article['source'].lower(),
            'image_url': article['image_url'],
            'categories': article['categories'],
            'language': article['language'],
            'country': None,
            'published_at': datetime.fromisoformat(article['published_at'].replace('Z', '+00:00'))
        } for article in articles]
        return formatted_articles


class NewsAPIorgAPI(NewsAPIBase):
    """
    Interface to NewsAPI.org - https://newsapi.org/docs/endpoints/everything
    """
    base_url = 'https://newsapi.org/v2'
    last_updated = 0
    max_freq_s = 1000

    def get_sources(self, page=1, **kwargs):
        """
        News Data Sources
        https://www.thenewsapi.com/documentation
        """
        params = {
            'category': kwargs.get('categories'),
            'language': kwargs.get('languages') or 'en',
            'country': kwargs.get('country') or 'us',
        }
        return self.send_request(f'{NewsAPIorgAPI.base_url}/top-headlines/sources', params)

    def get_top_stories(self, page=1, **kwargs):
        """
        News Data Sources
        https://www.thenewsapi.com/documentation
        """
        params = {
            'q': kwargs.get('search') or 'the',
            'country': kwargs.get('country') or 'us',
            'category': kwargs.get('categories'),
            'sources': kwargs.get('sources'),
            'pageSize': kwargs.get('pageSize') or 3,
            'page': kwargs.get('page') or page,
        }
        return self.send_request(f'{NewsAPIorgAPI.base_url}/top-headlines', params)

    def get_live_articles(self, page=1, **kwargs):
        """
        News Data Sources
        https://www.thenewsapi.com/documentation
        """
        params = {
            'apiKey': Config.NEWSAPI_ORG_API_KEY,
            'q': kwargs.get('search') or 'the',
            'searchIn': kwargs.get('searchIn'),
            'sources': kwargs.get('sources'),
            'domains': kwargs.get('domains'),
            'excludeDomains': kwargs.get('excludeDomains'),
            'from': kwargs.get('from'),
            'to': kwargs.get('to'),
            'language': kwargs.get('languages') or 'en',
            'sortBy': kwargs.get('sortBy') or 'publishedAt',
            'pageSize': kwargs.get('pageSize') or 3,
            'page': kwargs.get('page') or page,
        }
        return self.send_request(f'{NewsAPIorgAPI.base_url}/everything', params)

    def get_historical_articles(self, start_date: datetime, end_date: datetime = None, page=1, **kwargs):
        if end_date is not None:
            to_date = end_date
        else:
            to_date = start_date + timedelta(days=1)
        params = {
            'apiKey': Config.NEWSAPI_ORG_API_KEY,
            'from': start_date.strftime("%Y-%m-%d"),
            'to': to_date.strftime("%Y-%m-%d"),
            'q': kwargs.get('search', 'the'),
            'searchIn': kwargs.get('searchIn'),
            'sources': kwargs.get('sources'),
            'domains': kwargs.get('domains'),
            'excludeDomains': kwargs.get('excludeDomains'),
            'language': kwargs.get('languages', 'en'),
            'sortBy': kwargs.get('sortBy', 'publishedAt'),
            'pageSize': kwargs.get('pageSize', 3),
            'page': kwargs.get('page', page),
        }
        if end_date is not None and end_date > start_date:
            params['published_after'] = start_date.strftime("%Y-%m-%d")
            params['published_before'] = end_date.strftime("%Y-%m-%d")
        else:
            params['published_on'] = start_date.strftime("%Y-%m-%d")
        return self.send_request(f'{NewsAPIorgAPI.base_url}/everything', params)

    def format_articles(self, data: dict):
        """
        Parse the articles from the live data into the standard article format
        """
        if data is None or 'articles' not in data:
            return None
        articles = data['articles']
        formatted_articles = [{
            'native_id': NewsAPIBase.hash_string_sha256(article['title'] + article['description']),
            'adapter': 'NewsAPIorgAPI',
            'channel': NewsAPIBase.extract_domain(article['url']),
            'author': [art.strip() for art in (article.get('author') or '').lower().split(',')],
            'title': article['title'],
            'description': article['description'],
            'url': article['url'],
            'source': article['source']['name'],
            'image_url': article['urlToImage'],
            'categories': None,
            'language': 'en',
            'country': None,
            'published_at': datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
        } for article in articles]
        return formatted_articles


class NewsHistorian:
    """
    Gather and cache historical data from a News source
    """

    def __init__(self, news_api: NewsAPIBase):
        self.news_api = news_api
        self.fpath = os.path.join(Config.RAW_DATA_DIR, 'news', str(news_api.__class__.__name__.lower()) + '.feather')
        if os.path.isfile(self.fpath):
            self.data_df = pd.read_feather(self.fpath)
            self.start_date = min(self.data_df['published_at'])
        else:
            self.data_df = None
            self.start_date = datetime.utcnow()

    def gather_daily_data(self, days_offset=0):
        current_day = self.start_date - timedelta(days=days_offset)
        articles = self.news_api.get_historical_articles(start_date=current_day, page=1)
        article_list = self.news_api.format_articles(articles)
        pagination = articles.get('pagination', articles.get('meta'))
        total = pagination.get('total', pagination.get('found'))
        pages = math.ceil(total / pagination['limit'])
        print(f'=== gathering {current_day=} : {pages=} {pagination=}')
        data_df = None
        time.sleep(5)
        for page in range(2, min(pages, 199)):
            print(f'{page=} of {pages=}')
            # Query for articles and retry a few times before raising an error.
            articles = self.news_api.get_historical_articles(start_date=current_day, page=page)
            if articles is None:
                time.sleep(30)
                articles = self.news_api.get_historical_articles(start_date=current_day, page=page)
            if articles is None:
                time.sleep(300)
                articles = self.news_api.get_historical_articles(start_date=current_day, page=page)
            if articles is None:
                raise ConnectionError(f'Could not connect to api for {self.news_api} {current_day=} {page=}')
            print('    formatting...')
            article_list += self.news_api.format_articles(articles)
            print('    de-duplicating...')
            new_df = pd.DataFrame(article_list)
            new_df = new_df.drop_duplicates(subset='native_id', keep='last')
            new_df['domain'] = new_df['url'].apply(NewsAPIBase.extract_domain)
            print('    concatenating...')
            if data_df is None:
                data_df = new_df.copy()
            else:
                data_df = pd.concat([data_df, new_df])
            article_list = []
            time.sleep(2)
        self.data_df = pd.concat([self.data_df, data_df])
        self.data_df.to_feather(self.fpath)

    def gather_history(self, total_days):
        for day_idx in range(total_days):
            self.gather_daily_data(days_offset=day_idx)
            print(f"Before dedupe {self.data_df.shape=}")
            self.data_df = self.data_df.drop_duplicates(subset='native_id', keep='last')
            print(f"After dedupe {self.data_df.shape=}")
        print('DONE!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    def list_missing_dates(self):
        df = self.data_df.copy()
        # Normalize to dates (if your datetime includes times)
        df['dates'] = df['datetime'].dt.date
        # Find the earliest date and today's date
        earliest_date = df['dates'].min()
        today_date = datetime.now().date()  # Ensure we're working with dates for comparison
        # Generate a complete date range
        date_range = pd.date_range(start=earliest_date, end=today_date).date
        # Find unique dates in the DataFrame
        unique_dates_in_df = df['dates'].unique()
        # Convert date_range and unique_dates_in_df to sets for comparison
        missing_dates = set(date_range) - set(unique_dates_in_df)
        # Convert to a list and sort, if desired
        missing_dates_list = sorted(list(missing_dates))
        print("Dates not present in the DataFrame:", missing_dates_list)


class NewsParser:
    # List of blacklisted keywords
    blacklisted_keywords = ['Daily Outlook', 'bitcoin', 'trump', 'musk', 'elon musk', 'tesla', 'remove from watchlist',
                            'zacks.com', 'meghan markle', 'taylor swift', 'kanye', 'kardashian']
    # Create a regex pattern to match any of the blacklisted keywords
    blacklisted_pattern = '|'.join(blacklisted_keywords)
    # The sources to be excluded from financial news analysis
    blacklisted_domains = []  # get_banned_sources()
    # Strings to be removed from news articles without invalidating the whole article
    dead_strings = ['By Reuters', '/PRNewswire/ -- ', 'Exclusive-', '-sources', ' By Investing.com']

    def __init__(self, news_df: pd.DataFrame, df_name, is_finance: bool = True):
        if is_finance:
            # Filter the non-finance domains
            news_df = news_df.loc[~news_df['domain'].isin(self.blacklisted_domains), :]
        # Use vectorized str.contains to find rows with blacklisted keywords in either column
        blacklisted_titles = news_df['title'].str.contains(self.blacklisted_pattern, case=False, na=False)
        blacklisted_descriptions = news_df['description'].str.contains(self.blacklisted_pattern, case=False, na=False)
        # Filter the DataFrame by inverting the condition (keeping rows that do not match the blacklisted pattern)
        news_df = news_df[~(blacklisted_titles | blacklisted_descriptions)]
        news_df['title'] = news_df['title'].apply(self.preprocess_content)
        news_df['description'] = news_df['description'].apply(self.preprocess_content)
        self.news_df = news_df.sort_values(by='published_at').reset_index(drop=True)
        self.df_name = df_name

    @classmethod
    def preprocess_content(cls, content):
        content = str(content or "").replace('"', "'").replace('\t', "")
        for ds in cls.dead_strings:
            content = content.replace(ds, '')
        return StringParser.remove_non_ascii(content)

    def get_headlines(self):
        return self.news_df.apply(
            lambda x: f"title: {x['title']}\ndescription: {x['description']}", axis=1)

    def get_content(self):
        return self.news_df.apply(
            lambda x: '{' + ',\n'.join([f'"{col}": "{x[col]}"' for col in
                                        ('domain', 'published_at',
                                         'author', 'title', 'description', 'body')]) + '}', axis=1)

    @staticmethod
    def get_company_aliases():
        tickers = pd.read_csv(os.path.join(Config.DATA_DIR, 'raw', 'finance', 'tickers_with_alias.csv'), sep='\t',
                              index_col='Unnamed: 0')
        symbols = tickers['Symbol'].str.lower().to_list()[:50]
        aliases = tickers['aliases'].str.lower().to_list()[:50]
        alias_lookup = {alias.strip().lower(): symbols[idx].upper() for idx in range(len(aliases)) for alias in
                        aliases[idx].split(',')}
        alias_lookup.pop('tesla')
        alias_lookup.pop('visa')
        return alias_lookup

    @staticmethod
    def is_news_item_finance(news_title, finance_aliases):
        finance_aliases = set(finance_aliases)
        title = news_title.lower()
        return any([alias in title for alias in finance_aliases])

    def filter_to_finance_news(self, aliases: set = None):
        if aliases is None:
            aliases = set(self.get_company_aliases().keys())
        return self.news_df.loc[
                       self.news_df['title'].apply(lambda x: self.is_news_item_finance(x, aliases)), :].copy()
