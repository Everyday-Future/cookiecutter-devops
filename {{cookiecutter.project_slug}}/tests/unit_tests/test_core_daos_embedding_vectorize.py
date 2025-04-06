import os
import pytest
import numpy as np
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from core.daos.embedding.dimensionality_reduction import PCAReducer, TruncationReducer, BaseReducer
from core.daos.embedding.search_embedding_model import SearchEmbeddingModel


class TestEmbeddingsGenerator:
    """Test suite for the EmbeddingsGenerator class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Clean up after test
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_texts(self):
        """Sample texts for testing embeddings."""
        return [
            "This is a test sentence.",
            "Another sample text for embedding.",
            "Machine learning is fascinating."
        ]

    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock SentenceTransformer to avoid loading actual models during tests."""
        with patch('core.daos.embedding.search_embedding_model.SentenceTransformer') as mock_st:
            # Configure the mock to return a fixed embedding dimension
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384

            # Make encode return predictable embeddings of the right shape
            def mock_encode(texts, batch_size=None, show_progress_bar=None):
                if isinstance(texts, str):
                    return np.ones(384)  # Single text
                else:
                    return np.ones((len(texts), 384))  # Multiple texts

            mock_model.encode.side_effect = mock_encode
            mock_st.return_value = mock_model
            yield mock_st

    @pytest.fixture
    def mock_pca_reducer(self):
        """Create a mock PCA reducer that's safe for pickling."""

        # Create a custom mock class for the reducer that can be safely pickled
        # by avoiding MagicMock methods and using a simpler structure
        class MockReducer(BaseReducer):
            def __init__(self, n_components=2):
                self.n_components = n_components
                self._fitted = False
                # Simple flag to track if transform was called
                self.transform_called = False

            def _check_is_fitted(self):
                return self._fitted

            def fit(self, data):
                self._fitted = True

            def transform(self, data):
                self.transform_called = True
                # Return data with reduced dimensions
                return np.ones((data.shape[0], self.n_components))

            def fit_transform(self, data):
                self.fit(data)
                return self.transform(data)

        return MockReducer

    def test_init_and_load_model(self, mock_sentence_transformer):
        """Test initialization and model loading."""
        model_name = "test-model"
        generator = SearchEmbeddingModel(model_name=model_name)

        # Check if the model was loaded with correct name
        mock_sentence_transformer.assert_called_once_with(model_name)
        assert generator.model_name == model_name
        assert generator.reducer is None

    def test_init_with_reducer(self, mock_sentence_transformer, mock_pca_reducer):
        """Test initialization with a dimensionality reducer."""
        reducer = mock_pca_reducer(n_components=50)
        generator = SearchEmbeddingModel(reducer=reducer)

        assert generator.reducer is reducer
        assert generator.reducer.n_components == 50

    def test_get_embedding_single_text(self, mock_sentence_transformer):
        """Test getting embedding for a single text."""
        generator = SearchEmbeddingModel()
        embedding = generator.get_embedding("Test text")

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (30,)  # Based on our mock
        generator.model.encode.assert_called_once()

    def test_get_embedding_invalid_input(self, mock_sentence_transformer):
        """Test that get_embedding raises ValueError for invalid inputs."""
        generator = SearchEmbeddingModel()

        with pytest.raises(ValueError):
            generator.get_embedding("")

        with pytest.raises(ValueError):
            generator.get_embedding(None)

        with pytest.raises(ValueError):
            generator.get_embedding(123)

    def test_get_embedding_with_reducer(self, mock_sentence_transformer, mock_pca_reducer):
        """Test getting embedding with dimensionality reduction."""
        # Create a reducer that's pre-fitted
        reducer = mock_pca_reducer(n_components=50)
        reducer._fitted = True  # Set it as fitted

        generator = SearchEmbeddingModel(reducer=reducer)
        embedding = generator.get_embedding("Test text with reduction")

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (50,)  # Reduced dimensions
        assert reducer.transform_called is True

    def test_get_embeddings_multiple_texts(self, mock_sentence_transformer, sample_texts):
        """Test getting embeddings for multiple texts."""
        generator = SearchEmbeddingModel()
        embeddings = generator.get_embeddings(sample_texts)

        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (len(sample_texts), 384)
        generator.model.encode.assert_called_once()

    def test_get_embeddings_empty_list(self, mock_sentence_transformer):
        """Test that get_embeddings raises ValueError for empty list."""
        generator = SearchEmbeddingModel()

        with pytest.raises(ValueError):
            generator.get_embeddings([])

    def test_get_embeddings_with_fit_reducer(self, mock_sentence_transformer, sample_texts, mock_pca_reducer):
        """Test getting embeddings with fitting reducer on-the-fly."""
        # Use our custom mock reducer instead of MagicMock
        reducer = mock_pca_reducer(n_components=50)

        generator = SearchEmbeddingModel(reducer=reducer)
        embeddings = generator.get_embeddings(sample_texts, fit_reducer=True)

        # Verify the reducer was fitted and transform was called
        assert reducer._fitted is True
        assert reducer.transform_called is True
        assert embeddings.shape == (len(sample_texts), 50)

    def test_fit_reducer(self, mock_sentence_transformer):
        """Test fitting a reducer on embeddings."""
        # Use TruncationReducer instead of PCAReducer for more predictable behavior
        reducer = TruncationReducer(n_components=2)
        generator = SearchEmbeddingModel(reducer=reducer)

        # Create sample embeddings to fit
        embeddings = np.random.rand(10, 384)
        generator.fit_reducer(embeddings)

        # Check if reducer is fitted
        assert reducer.is_fitted

    def test_fit_reducer_no_reducer(self, mock_sentence_transformer):
        """Test fit_reducer when no reducer is set."""
        generator = SearchEmbeddingModel(reducer=None)
        embeddings = np.random.rand(10, 384)

        # Should not raise an error, just log a message
        generator.fit_reducer(embeddings)

    def test_fit_reducer_invalid_inputs(self, mock_sentence_transformer, mock_pca_reducer):
        """Test fit_reducer with invalid inputs."""
        reducer = mock_pca_reducer(n_components=2)
        generator = SearchEmbeddingModel(reducer=reducer)

        with pytest.raises(ValueError):
            generator.fit_reducer("not an array")

        with pytest.raises(ValueError):
            generator.fit_reducer(np.array([1, 2, 3]))  # 1D array

    def test_fit_reducer_n_components_too_large(self, mock_sentence_transformer):
        """Test fit_reducer when n_components is larger than data dimensions."""
        # Create embeddings with 10 features
        embeddings = np.random.rand(5, 10)

        # Create TruncationReducer instead of PCAReducer to avoid sklearn validation
        reducer = TruncationReducer(n_components=20)
        generator = SearchEmbeddingModel(reducer=reducer)

        # Should adjust n_components automatically
        generator.fit_reducer(embeddings)
        assert reducer.n_components <= 10

    def test_save_and_load(self, mock_sentence_transformer, temp_dir):
        """Test saving and loading the generator with a real PCAReducer."""
        # Import the necessary components from scikit-learn directly
        from sklearn.decomposition import PCA

        # Create a real PCA model and manually set it as fitted
        pca_model = PCA(n_components=2)
        # Set minimal attributes to make it appear fitted
        pca_model.components_ = np.random.rand(2, 384)
        pca_model.mean_ = np.random.rand(384)
        pca_model.explained_variance_ = np.array([0.5, 0.3])
        pca_model.explained_variance_ratio_ = np.array([0.6, 0.4])
        pca_model.singular_values_ = np.array([1.0, 0.8])
        pca_model.n_components_ = 2
        pca_model.n_samples_ = 10
        pca_model.n_features_ = 384
        pca_model.n_features_in_ = 384

        # Create a PCAReducer with the pre-fitted model
        reducer = PCAReducer(n_components=2)
        reducer.model = pca_model

        # Create the generator with the reducer
        original_generator = SearchEmbeddingModel(
            model_name="test-model",
            reducer=reducer
        )

        # Save the generator
        save_path = os.path.join(temp_dir, "test_generator.pkl")
        original_generator.save(save_path)

        # Ensure file exists
        assert os.path.exists(save_path)

        # Load in a new generator
        with patch('core.daos.embedding.search_embedding_model.SentenceTransformer'):
            loaded_generator = SearchEmbeddingModel.load(save_path)

        # Verify properties were preserved
        assert loaded_generator.model_name == original_generator.model_name
        assert loaded_generator.reducer is not None
        assert loaded_generator.reducer.n_components == 2
        assert loaded_generator.reducer.is_fitted

    def test_load_nonexistent_file(self):
        """Test loading from a non-existent file."""
        with pytest.raises(FileNotFoundError):
            SearchEmbeddingModel.load("nonexistent_file.pkl")

    def test_load_corrupt_file(self, temp_dir):
        """Test loading from a corrupt file."""
        # Create a corrupt file
        corrupt_path = os.path.join(temp_dir, "corrupt.pkl")
        with open(corrupt_path, 'w') as f:
            f.write("Not a valid pickle file")

        with pytest.raises(RuntimeError):
            SearchEmbeddingModel.load(corrupt_path)


class TestEmbeddingsGeneratorIntegration:
    """Integration tests for EmbeddingsGenerator using real models."""

    @pytest.fixture(scope="module")
    def temp_dir(self):
        """Create a temporary directory for test files that persists for the module."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Clean up after all tests in this class
        shutil.rmtree(temp_dir)

    def test_real_sentence_transformer(self):
        """Test with a real SentenceTransformer model (requires internet)."""
        # Use a tiny model for faster tests
        generator = SearchEmbeddingModel(model_name="all-MiniLM-L6-v2")
        embedding = generator.get_embedding("Integration test with real model")

        # Check that we got a real embedding
        assert embedding.shape[0] > 0
        assert not np.all(embedding == 0)

    def test_real_save_load_cycle(self, temp_dir):
        """Test a complete save/load cycle with real components."""
        # Create a generator with a real TruncationReducer (not PCA)
        reducer = TruncationReducer(n_components=10)  # TruncationReducer is always fitted
        generator = SearchEmbeddingModel(
            model_name="all-MiniLM-L6-v2",
            reducer=reducer
        )

        # Generate an embedding before saving
        original_embedding = generator.get_embedding("Test text for real save/load cycle")

        # Save the generator
        save_path = os.path.join(temp_dir, "real_generator.pkl")
        generator.save(save_path)

        # Load in a new generator
        loaded_generator = SearchEmbeddingModel.load(save_path)

        # Generate the same embedding with loaded generator
        loaded_embedding = loaded_generator.get_embedding("Test text for real save/load cycle")

        # Embeddings should be identical
        np.testing.assert_array_equal(original_embedding, loaded_embedding)

    def test_full_pipeline_with_pca(self, temp_dir):
        """Test the full pipeline including PCA fitting and application."""
        # Create sample texts for testing - need more samples than components
        texts = [
            "Machine learning is a subset of artificial intelligence.",
            "Natural language processing helps computers understand human language.",
            "Deep learning models can recognize patterns in data.",
            "Dimensionality reduction techniques help visualize high-dimensional data.",
            "Neural networks are inspired by the human brain.",
            "Support vector machines are effective for classification tasks.",
            "Reinforcement learning uses rewards to guide decision making.",
            "Clustering algorithms group similar data points together.",
            "Feature engineering transforms raw data into useful features.",
            "Cross-validation helps evaluate model performance.",
            "Ensemble methods combine multiple models for better predictions.",
            "Transfer learning uses knowledge from one task to help with another.",
            "Overfitting occurs when a model learns noise in the training data.",
            "Underfitting happens when a model is too simple to capture patterns.",
            "Hyperparameter tuning optimizes model parameters.",
            "Data preprocessing cleans and transforms raw data.",
            "Regularization helps prevent overfitting in machine learning models.",
            "Decision trees split data based on feature values.",
            "Gradient descent is an optimization algorithm for training models.",
            "Backpropagation calculates gradients in neural networks.",
            "Random forests combine multiple decision trees.",
            "Anomaly detection identifies outliers in data."
        ]

        # Now we have 22 samples, so we can safely use 20 components
        reducer = PCAReducer(n_components=20)
        generator = SearchEmbeddingModel(
            model_name="all-MiniLM-L6-v2",
            reducer=reducer
        )

        # Generate embeddings and fit PCA in one step
        embeddings = generator.get_embeddings(texts, fit_reducer=True)

        # Check the dimensionality was reduced
        assert embeddings.shape[1] == 20
        assert reducer.is_fitted

        # Save the generator with fitted PCA
        save_path = os.path.join(temp_dir, "pca_generator.pkl")
        generator.save(save_path)

        # Load the generator
        loaded_generator = SearchEmbeddingModel.load(save_path)

        # Ensure PCA was properly saved and loaded
        assert loaded_generator.reducer is not None
        assert loaded_generator.reducer.is_fitted

        # Generate embedding for a new text
        new_embedding = loaded_generator.get_embedding("This is a new text that wasn't in the training set.")

        # Ensure it has the reduced dimensionality
        assert new_embedding.shape[0] == 20