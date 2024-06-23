"""

Background Investigation Tools

Learn more about a given subject's background and history
Age out and refresh the cached data after a specified interval


Wikipedia
https://wikipedia.readthedocs.io/en/latest/quickstart.html#quickstart

SerpAPI - Google Search API
https://serpapi.com/dashboard

Google Fact Check Tools API
https://developers.google.com/fact-check/tools/api

"""
import wikipedia
import requests
import urllib
import urllib.request
from config import Config


class WikipediaAPI:
    @classmethod
    def get_summary(cls, topic):
        try:
            return wikipedia.summary(topic)
        except wikipedia.exceptions.PageError:
            return "Page not found"
        except wikipedia.exceptions.DisambiguationError as e:
            return f"Disambiguation page found, options include: {e.options}"

    @classmethod
    def search_articles(cls, query):
        search_results = wikipedia.search(query)
        summaries = []
        for result in search_results:
            try:
                summary = wikipedia.summary(result)
                summaries.append({'title': result, 'summary': summary})
            except wikipedia.exceptions.DisambiguationError:
                summaries.append({'title': result, 'summary': 'Disambiguation page found'})
        return summaries

    @classmethod
    def get_page(cls, title):
        try:
            page = wikipedia.page(title)
            return {
                'title': page.title,
                'url': page.url,
                'content': page.content
            }
        except wikipedia.exceptions.PageError:
            return "Page not found"
        except wikipedia.exceptions.DisambiguationError as e:
            return f"Disambiguation page found, options include: {e.options}"

    @classmethod
    def get_images(cls, title):
        try:
            page = wikipedia.page(title)
            return {
                'title': page.title,
                'images': page.images
            }
        except wikipedia.exceptions.PageError:
            return "Page not found"
        except wikipedia.exceptions.DisambiguationError as e:
            return f"Disambiguation page found, options include: {e.options}"


class SerpAPI:
    base_url = 'https://serpapi.com/search.json'

    @classmethod
    def request(cls, query_params):
        response = requests.get(cls.base_url, params=query_params)
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': 'Failed to fetch data'}

    @classmethod
    def get_google_search(cls, query):
        params = {
            'q': query,
            'api_key': Config.SERPAPI_API_KEY,
            'engine': 'google'
        }
        return cls.request(params)

    @classmethod
    def get_google_trends(cls, query):
        url = f'https://serpapi.com/search.html?engine=google_trends&q={query}&api_key={Config.SERPAPI_API_KEY}'
        data = urllib.request.urlopen(url)
        # Replace special Unicode characters with more common ones
        normalized_data = data.read().decode('utf-8')
        normalized_data = normalized_data.replace(r'\u2009', ' ').replace(r'\u2013', '-')
        return normalized_data

    @classmethod
    def get_google_patents(cls, query):
        url = f'https://serpapi.com/search.html?engine=google_patents&q={query}&api_key={Config.SERPAPI_API_KEY}'
        data = urllib.request.urlopen(url)
        # Replace special Unicode characters with more common ones
        normalized_data = data.read().decode('utf-8')
        normalized_data = normalized_data.replace(r'\u2009', ' ').replace(r'\u2013', '-')
        return normalized_data

    @classmethod
    def get_google_images(cls, query):
        params = {
            'q': query,
            'api_key': Config.SERPAPI_API_KEY,
            'engine': 'google_images'
        }
        return cls.request(params)

    @classmethod
    def get_google_news(cls, query):
        params = {
            'q': query,
            'api_key': Config.SERPAPI_API_KEY,
            'engine': 'google_news'
        }
        return cls.request(params)


class GoogleFactCheckToolsAPI:
    @classmethod
    def search_fact_check(cls, query):
        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {
            'query': query,
            'key': Config.FACT_CHECK_API_KEY,
            'languageCode': 'en'
        }
        response = requests.get(url, params=params)
        results = response.json()
        if 'claims' in results:
            for claim in results['claims']:
                text = claim['text']
                claimant = claim.get('claimant')
                print('claim', claim)
                claimDate = claim.get('claimDate')
                assessment = claim.get('claimReview', [{}])[0].get('textualRating', 'No rating found')
                # print(f"Claim: {text}\nClaimant: {claimant}\nDate: {claimDate}\nAssessment: {assessment}\n{results}")
        return results
