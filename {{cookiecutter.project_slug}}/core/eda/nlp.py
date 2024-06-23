import re
from joblib import load
from functools import lru_cache
from difflib import SequenceMatcher
import numpy as np
from spellchecker import SpellChecker
from gensim.models import KeyedVectors
from config import Config
from sklearn.metrics.pairwise import cosine_similarity


class NLP:
    """
    Stateless collection of NLP functions for use in search
    """
    # Lazy instance of SpellChecker()
    spell = None
    # Lazy instance of gensim similarity model
    similarity = None
    # Lazy instance of dimensionality reduction for queries
    pca = None
    # Cache for vocab vectors
    vocab = {}
    # Regular expression for finding contractions
    contractions_dict = {"ain't": "are not", "'s": " is", "aren't": "are not", "can't": "can not",
                         "can't've": "cannot have",
                         "'cause": "because", "could've": "could have", "couldn't": "could not",
                         "couldn't've": "could not have",
                         "didn't": "did not", "doesn't": "does not", "don't": "do not", "hadn't": "had not",
                         "hadn't've": "had not have",
                         "hasn't": "has not", "haven't": "have not", "he'd": "he would", "he'd've": "he would have",
                         "he'll": "he will",
                         "he'll've": "he will have", "how'd": "how did", "how'd'y": "how do you", "how'll": "how will",
                         "i'd": "i would",
                         "i'd've": "i would have", "i'll": "i will", "i'll've": "i will have", "i'm": "i am",
                         "i've": "i have",
                         "isn't": "is not", "it'd": "it would", "it'd've": "it would have", "it'll": "it will",
                         "it'll've": "it will have",
                         "let's": "let us", "ma'am": "madam", "mayn't": "may not", "might've": "might have",
                         "mightn't": "might not",
                         "mightn't've": "might not have", "must've": "must have", "mustn't": "must not",
                         "mustn't've": "must not have",
                         "needn't": "need not", "needn't've": "need not have", "o'clock": "of the clock",
                         "oughtn't": "ought not",
                         "oughtn't've": "ought not have", "shan't": "shall not", "sha'n't": "shall not",
                         "shan't've": "shall not have", "she'd": "she would", "she'd've": "she would have",
                         "she'll": "she will",
                         "she'll've": "she will have", "should've": "should have", "shouldn't": "should not",
                         "shouldn't've": "should not have", "so've": "so have", "that'd": "that would",
                         "that'd've": "that would have",
                         "there'd": "there would", "there'd've": "there would have",
                         "they'd": "they would", "they'd've": "they would have", "they'll": "they will",
                         "they'll've": "they will have",
                         "they're": "they are", "they've": "they have", "to've": "to have", "wasn't": "was not",
                         "we'd": "we would",
                         "we'd've": "we would have", "we'll": "we will", "we'll've": "we will have", "we're": "we are",
                         "we've": "we have",
                         "weren't": "were not", "what'll": "what will", "what'll've": "what will have",
                         "what're": "what are",
                         "what've": "what have", "when've": "when have", "where'd": "where did",
                         "where've": "where have", "who'll": "who will", "who'll've": "who will have",
                         "who've": "who have",
                         "why've": "why have", "will've": "will have", "won't": "will not", "won't've": "will not have",
                         "would've": "would have", "wouldn't": "would not", "wouldn't've": "would not have",
                         "y'all": "you all",
                         "y'all'd": "you all would", "y'all'd've": "you all would have", "y'all're": "you all are",
                         "y'all've": "you all have",
                         "you'd": "you would", "you'd've": "you would have", "you'll": "you will",
                         "you'll've": "you will have",
                         "you're": "you are", "you've": "you have"}
    contractions_re = re.compile('(%s)' % '|'.join(contractions_dict))

    @classmethod
    def load_cache(cls):
        if cls.spell is None:
            cls.spell = SpellChecker()
        if cls.similarity is None:
            cls.similarity = KeyedVectors.load(Config.SIMILARITY_MODEL)
        if cls.pca is None:
            cls.pca = load(Config.PCA_MODEL)

    @classmethod
    def cache_clear(cls):
        """
        Clear the cache df and _data_df
        :return:
        :rtype:
        """
        cls.spell = None
        cls.similarity = None
        cls.pca = None

    @staticmethod
    def cosine_similarity(vec_0, vec_1):
        return cosine_similarity(vec_0, vec_1).item()

    @classmethod
    @lru_cache(maxsize=3200)
    def did_you_mean(cls, search_phrase):
        """
        Suggest an alternative spelling after spellchecking.
        Returns an empty string if no recommendations are found.
        """
        if cls.spell is None:
            cls.load_cache()
        corrected = [cls.spell.correction(word) for word in search_phrase.split(' ')]
        corrected = ' '.join(corrected)
        if corrected != search_phrase:
            return corrected
        else:
            return ''

    @staticmethod
    @lru_cache(maxsize=3200)
    def string_similarity(str_a, str_b):
        """
        Compare two strings and get their difference in terms of % of overlapping characters
        """
        return SequenceMatcher(None, str_a, str_b).ratio()

    @classmethod
    @lru_cache(maxsize=3200)
    def get_similar_words(cls, keyword, n_similar=5, min_semantic_similarity=0.5, max_string_similarity=0.7):
        """
        Get similar words to an input keyword using a gensim model
        :param keyword: The keyword to find similar words
        :param n_similar: Maximum number of words to return
        :param min_semantic_similarity: Minimum distance that a word can be in meaning from the keyword
        :param max_string_similarity: Maximum string similarity with keyword.
            This prevents returning plural versions and other minor differences.
        """
        if cls.similarity is None:
            cls.load_cache()
        try:
            sim_list = cls.similarity.most_similar(keyword, topn=n_similar)
        except KeyError:
            # The keyword wasn't found in the similarity search, so just return the original keyword
            return [keyword]
        # Get similar keywords if they are semantically similar enough and different enough from the keyword
        keywords = [sim[0] for sim in sim_list
                    if (cls.string_similarity(keyword, sim[0]) < max_string_similarity) and
                    (sim[1] > min_semantic_similarity)]
        return [keyword] + keywords

    @classmethod
    def re_replace(cls, match):
        return cls.contractions_dict[match.group(0)]

    @classmethod
    def expand_contractions(cls, text):
        """
        Function for expanding contractions
        """
        return cls.contractions_re.sub(cls.re_replace, text)

    @staticmethod
    def clean_text(text):
        """
        Function for Cleaning Text
        """
        text = text.lower()
        text = text.strip()
        text = re.sub('\n', ' ', text)
        text = re.sub(r"http\S+", "", text)
        text = re.sub('[^a-z]', ' ', text)
        text = re.sub(' +', ' ', text)
        return text.strip()

    @staticmethod
    def dedupe_list(target_list):
        """
        Deduplicate a list while preserving order
        """
        seen = set()
        seen_add = seen.add
        return [x for x in target_list if not (x in seen or seen_add(x))]

    @classmethod
    @lru_cache(maxsize=3200)
    def get_embedding_w2v(cls, query, orig_query=None):
        """
        Function returning vector representation of a document
        """
        doc_tokens = query.split()
        if cls.similarity is None:
            cls.load_cache()
        embeddings = []
        if len(doc_tokens) < 1:
            return np.zeros(Config.PCA_DIMS)
        else:
            for tok in doc_tokens:
                cached_vec = cls.vocab.get(tok)
                if cached_vec is not None:
                    embeddings.append(cached_vec)
                elif tok in cls.similarity.key_to_index.keys():
                    vec = cls.similarity.get_vector(tok)
                    vec = cls.pca.transform(vec.reshape(1, -1))[0]
                    embeddings.append(vec)
                    cls.vocab[tok] = vec
                else:
                    embeddings.append(np.random.rand(Config.PCA_DIMS))
            if len(embeddings) == 0:
                raise KeyError(f'no results found for query "{orig_query or query}"')
            # mean the vectors of individual words to get the vector of the document
            return np.mean(embeddings, axis=0)

    @staticmethod
    def num_matches(query, body):
        """
        Count the number of occurrences of a keyword in a string
        """
        return sum([body.count(each_word) for each_word in query.split(' ')])

    @staticmethod
    def expand_keywords(query, n_similar=5, min_semantic_similarity=0.5, max_string_similarity=0.7):
        """
        Get the synonyms for keywords in a query
        TODO - remove stopwords, add stemming/lemmatization
        """
        keywords = []
        for word in query.split(' '):
            keywords += NLP.get_similar_words(word,
                                              n_similar=n_similar,
                                              min_semantic_similarity=min_semantic_similarity,
                                              max_string_similarity=max_string_similarity)
        return NLP.dedupe_list(keywords)
