"""

Arxiv API

https://info.arxiv.org/help/api/basics.html

No more than one request every 3 seconds

"""
import urllib
import urllib.request


class Arxiv:
    """
    Interface to the Arxiv research server
    """
    @classmethod
    def get_search_results(cls, query='electron', page=0):
        url = f'http://export.arxiv.org/api/query?search_query=all:{query}&start={page}&max_results=10'
        data = urllib.request.urlopen(url)
        results = data.read().decode('utf-8')
        return results


"""

Semantic Scholar aka S2

Rate limit:
    1 request per second for the following endpoints:
        /paper/batch
        /paper/search
        /recommendations
    10 requests / second for all other calls

https://www.semanticscholar.org/product/api/tutorial

"""


class SemanticScholarAPI:
    """
    Get research papers about a given topic
    """
    @classmethod
    def search_papers(cls, query_str='quantum computing'):
        # Define the API endpoint URL
        url = 'https://api.semanticscholar.org/graph/v1/paper/search'
        # More specific query parameter
        query_params = {'query': query_str,
                        'limit': 10,
                        'offset': 0}
        # Define headers with API key
        headers = {'x-api-key': Config.SEMANTIC_SCHOLAR_API_KEY}
        # Send the API request
        response = requests.get(url, params=query_params, headers=headers)
        # Check response status
        if response.status_code == 200:
            response_data = response.json()
            # Process and print the response data as needed
            return response_data
        else:
            print(f"Request failed with status code {response.status_code}: {response.text}")


"""

CORE API

CORE papers search API
Rate Limit = 10,000 tokens per day, maximum 10 per minute.

https://api.core.ac.uk/docs/v3

"""
from config import Config


class CorePapersAPI:
    """
    Interface to CORE Papers
    """
    api_key = Config.CORE_PAPERS_API_KEY
    base_url = "https://api.core.ac.uk/v3/"

    def __init__(self, api_key):
        self.base_url = "https://api.core.ac.uk/v3/"
        self.api_key = api_key

    @classmethod
    def search_articles(cls, query, page=1, pageSize=10):
        headers = {'Authorization': f'Bearer {cls.api_key}'}
        """Search articles in the CORE API."""
        params = {
            'q': query,
            'page': page,
            'pageSize': pageSize
        }
        response = requests.get(f"{cls.base_url}articles/search", headers=headers, params=params)
        return response.json()

    @classmethod
    def search_papers(cls):
        pass


"""

PubMed

https://pubmed.ncbi.nlm.nih.gov/

"""
import requests
from config import Config


class PubMedClient:
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    @classmethod
    def search(cls, term, max_results=100):
        """
        Search articles in PubMed with the given search term and maximum results limit.
        """
        params = {
            "db": "pubmed",
            "term": term,
            "retmax": max_results,
            "email": Config.EMAIL_ADDRESS,
            "tool": "my_tool",  # Replace with your tool name
            # "api_key": "your_api_key"  # Optional: Use if you have an API key
        }
        response = requests.get(f"{cls.base_url}research.fcgi", params=params)
        if response.status_code == 200:
            return response.text
        else:
            response.raise_for_status()

    @classmethod
    def fetch_details(cls, id_list):
        """
        Fetch details for a list of PubMed IDs.
        """
        ids = ','.join(map(str, id_list))
        params = {
            "db": "pubmed",
            "id": ids,
            "retmode": "json",
            # "email": self.email,
            "tool": "my_tool",  # Replace with your tool name
            # "api_key": "your_api_key"  # Optional: Use if you have an API key
        }
        response = requests.get(f"{cls.base_url}prefetch.fcgi", params=params)
        if response.status_code == 200:
            return response.text
        else:
            response.raise_for_status()



