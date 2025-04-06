import pytest
import numpy as np
import os
from unittest.mock import patch
from core.daos.embedding.dimensionality_reduction import (
    BaseReducer, PCAReducer, TruncationReducer, ReducerFactory
)


@pytest.fixture
def sample_data():
    return np.random.rand(100, 768)  # 100 samples with 768 features each


@pytest.fixture
def small_sample_data():
    return np.random.rand(20, 50)  # 20 samples with 50 features each


# Test BaseReducer functionality through a minimal concrete implementation
class MinimalReducer(BaseReducer):
    """Minimal implementation of BaseReducer for testing."""

    def _check_is_fitted(self):
        return self.model is not None

    def fit(self, data):
        self._validate_input(data)
        self.model = "fitted"

    def transform(self, data):
        self._validate_input(data)
        if not self.is_fitted:
            raise ValueError("Model not fitted")
        return data[:, :self.n_components]

    def fit_transform(self, data):
        self.fit(data)
        return self.transform(data)


class TestBaseReducer:
    def test_init(self):
        reducer = MinimalReducer(n_components=10)
        assert reducer.n_components == 10
        assert reducer.model is None
        assert not reducer.is_fitted

    def test_validate_input(self, sample_data):
        reducer = MinimalReducer()
        # Valid input
        reducer._validate_input(sample_data)

        # Invalid inputs
        with pytest.raises(ValueError, match="should be a numpy array"):
            reducer._validate_input([1, 2, 3])

        with pytest.raises(ValueError, match="should be a 2D array"):
            reducer._validate_input(np.array([1, 2, 3]))

    def test_preprocess_data(self, sample_data):
        reducer = MinimalReducer()
        processed = reducer.preprocess_data(sample_data)
        assert processed.shape == sample_data.shape
        # Check normalization (mean should be close to 0, std close to 1)
        assert np.abs(np.mean(processed)) < 1e-10
        assert np.abs(np.std(processed) - 1.0) < 1e-10

        # Test with a column having zero std deviation
        zero_std_data = np.copy(sample_data)
        zero_std_data[:, 0] = 1.0  # Set first column to constant
        processed = reducer.preprocess_data(zero_std_data)
        assert not np.any(np.isnan(processed))  # No NaNs due to division by zero

    def test_save_load(self, tmp_path, sample_data):
        reducer = MinimalReducer()
        file_path = tmp_path / "test_model.joblib"

        # Trying to save before fitting should raise an error
        with pytest.raises(ValueError, match="not been fitted"):
            reducer.save(str(file_path))

        # Fit and save
        reducer.fit(sample_data)
        reducer.save(str(file_path))
        assert os.path.exists(file_path)

        # Load into a new reducer
        new_reducer = MinimalReducer()
        new_reducer.load(str(file_path))
        assert new_reducer.is_fitted


class TestPCA:
    def test_pca_init(self):
        pca_reducer = PCAReducer(n_components=50)
        assert pca_reducer.n_components == 50
        assert pca_reducer.model is None

    def test_pca_fit(self, sample_data):
        pca_reducer = PCAReducer(n_components=50)
        pca_reducer.fit(sample_data)
        assert pca_reducer.model is not None
        assert pca_reducer.is_fitted

    def test_pca_transform(self, sample_data):
        pca_reducer = PCAReducer(n_components=50)
        pca_reducer.fit(sample_data)
        transformed_data = pca_reducer.transform(sample_data)
        assert transformed_data.shape == (100, 50)

    def test_pca_fit_transform(self, sample_data):
        pca_reducer = PCAReducer(n_components=50)
        transformed_data = pca_reducer.fit_transform(sample_data)
        assert transformed_data.shape == (100, 50)

    def test_pca_save_and_load(self, tmp_path, sample_data):
        file_path = tmp_path / "pca_model.joblib"
        pca_reducer = PCAReducer(n_components=50)
        pca_reducer.fit(sample_data)
        pca_reducer.save(str(file_path))

        # Ensure the file is created
        assert os.path.exists(file_path)

        # Load the model
        loaded_pca_reducer = PCAReducer(n_components=50)
        loaded_pca_reducer.load(str(file_path))

        # Ensure the model was loaded correctly
        assert loaded_pca_reducer.model is not None
        assert loaded_pca_reducer.is_fitted

        # Transform new data with the loaded model
        new_data = np.random.rand(10, 768)  # 10 new samples with 768 features each
        new_transformed_data = loaded_pca_reducer.transform(new_data)
        assert new_transformed_data.shape == (10, 50)

    def test_pca_transform_without_fit(self, sample_data):
        pca_reducer = PCAReducer(n_components=50)
        with pytest.raises(ValueError, match="not been fitted"):
            pca_reducer.transform(sample_data)

    def test_pca_explained_variance_ratio(self, sample_data):
        pca_reducer = PCAReducer(n_components=10)
        pca_reducer.fit(sample_data)
        var_ratio = pca_reducer.get_explained_variance_ratio()
        assert len(var_ratio) == 10
        assert np.all(var_ratio >= 0) and np.all(var_ratio <= 1)

        # Test before fitting
        pca_reducer = PCAReducer(n_components=10)
        with pytest.raises(RuntimeError, match="not fitted yet"):
            pca_reducer.get_explained_variance_ratio()


class TestTruncationReducer:
    def test_truncation_init(self):
        truncation_reducer = TruncationReducer(n_components=50)
        assert truncation_reducer.n_components == 50
        # TruncationReducer is always considered fitted after initialization
        assert truncation_reducer.is_fitted is True

    def test_truncation_fit(self, sample_data):
        truncation_reducer = TruncationReducer(n_components=50)
        truncation_reducer.fit(sample_data)
        assert truncation_reducer.is_fitted is True

    def test_truncation_transform(self, sample_data):
        truncation_reducer = TruncationReducer(n_components=50)
        transformed_data = truncation_reducer.transform(sample_data)
        assert transformed_data.shape == (100, 50)
        # Verify it's the first 50 columns
        np.testing.assert_array_equal(transformed_data, sample_data[:, :50])

    def test_truncation_fit_transform(self, sample_data):
        truncation_reducer = TruncationReducer(n_components=50)
        transformed_data = truncation_reducer.fit_transform(sample_data)
        assert transformed_data.shape == (100, 50)
        # Verify it's the first 50 columns
        np.testing.assert_array_equal(transformed_data, sample_data[:, :50])

    def test_truncation_n_components_larger_than_data(self, small_sample_data):
        # small_sample_data has 50 features, but we request 100
        truncation_reducer = TruncationReducer(n_components=100)
        truncation_reducer.fit(small_sample_data)
        # Should adjust n_components to the maximum available
        transformed_data = truncation_reducer.transform(small_sample_data)
        assert transformed_data.shape == (20, 50)
        np.testing.assert_array_equal(transformed_data, small_sample_data)


class TestReducerFactory:
    def test_get_reducer(self):
        # Test getting each type of reducer
        pca_reducer = ReducerFactory.get_reducer('pca', n_components=10)
        assert isinstance(pca_reducer, PCAReducer)
        assert pca_reducer.n_components == 10

        truncation_reducer = ReducerFactory.get_reducer('truncation', n_components=30)
        assert isinstance(truncation_reducer, TruncationReducer)
        assert truncation_reducer.n_components == 30

        # Test case insensitivity
        pca_upper = ReducerFactory.get_reducer('PCA', n_components=10)
        assert isinstance(pca_upper, PCAReducer)

        # Test invalid type
        with pytest.raises(ValueError, match="Unsupported reducer type"):
            ReducerFactory.get_reducer('invalid_type')

    @patch('core.daos.embedding.dimensionality_reduction.logger')
    def test_get_available_reducer_success(self, mock_logger, tmp_path, sample_data):
        # Create a PCA model to load
        pca_path = tmp_path / "pca_model.joblib"
        pca = PCAReducer(n_components=10)
        pca.fit(sample_data)
        pca.save(str(pca_path))

        # Test successful loading
        model_paths = {'pca': str(pca_path)}
        reducer = ReducerFactory.get_available_reducer(
            ['pca', 'umap', 'truncation'],
            model_paths,
            n_components=10
        )

        assert isinstance(reducer, PCAReducer)
        assert reducer.is_fitted
        mock_logger.info.assert_called_with(
            f"Successfully loaded pca model from {str(pca_path)}"
        )

    @patch('core.daos.embedding.dimensionality_reduction.logger')
    def test_get_available_reducer_fallback(self, mock_logger):
        # Test fallback when no models can be loaded
        model_paths = {'pca': 'nonexistent_path.joblib', 'umap': 'another_nonexistent.joblib'}
        reducer = ReducerFactory.get_available_reducer(
            ['pca', 'umap', 'truncation'],
            model_paths,
            n_components=10
        )

        assert isinstance(reducer, TruncationReducer)
        mock_logger.info.assert_called_with(
            "Falling back to TruncationReducer as no other models could be loaded"
        )

    @patch('core.daos.embedding.dimensionality_reduction.logger')
    def test_get_available_reducer_skip_unsupported(self, mock_logger):
        # Test skipping unsupported reducer types
        reducer = ReducerFactory.get_available_reducer(
            ['invalid_type', 'truncation'],
            {},
            n_components=10
        )

        assert isinstance(reducer, TruncationReducer)
        mock_logger.warning.assert_called_with(
            "Unsupported reducer type: invalid_type. Skipping."
        )
