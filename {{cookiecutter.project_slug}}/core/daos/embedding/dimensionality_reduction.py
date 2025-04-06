# core/daos/embedding/dimensionality_reduction.py
import numpy as np
import joblib
from typing import Type, Dict, List
from sklearn.decomposition import PCA
from config import logger
from abc import ABC, abstractmethod


class BaseReducer(ABC):
    """
    Abstract base class that defines the interface for all dimensionality reducers
    and implements common functionality.
    """

    def __init__(self, n_components: int = 2, **kwargs):
        """
        Initialize the dimensionality reducer.

        :param n_components: Number of dimensions to reduce to
        :type n_components: int
        """
        self.n_components = n_components
        self.model = None

    @property
    def is_fitted(self) -> bool:
        """
        Check if the model has been fitted.

        :returns: True if the model has been fitted, False otherwise
        :rtype: bool
        """
        return self._check_is_fitted()

    @abstractmethod
    def _check_is_fitted(self) -> bool:
        """
        Implementation-specific check for whether the model is fitted.

        :returns: True if the model has been fitted, False otherwise
        :rtype: bool
        """
        pass

    @staticmethod
    def _validate_input(x_train: np.ndarray) -> None:
        """
        Validate the input data.

        :param x_train: Data to validate
        :type x_train: np.ndarray
        :raises ValueError: If input data is not a numpy array or not 2D
        """
        if not isinstance(x_train, np.ndarray):
            raise ValueError("Input data should be a numpy array.")
        if x_train.ndim != 2:
            raise ValueError("Input data should be a 2D array.")

    def preprocess_data(self, x_train: np.ndarray) -> np.ndarray:
        """
        Preprocess the data (e.g., normalization).

        :param x_train: Data to preprocess
        :type x_train: np.ndarray
        :returns: Preprocessed data
        :rtype: np.ndarray
        """
        self._validate_input(x_train)
        mean = np.mean(x_train, axis=0)
        std = np.std(x_train, axis=0)
        # Handle columns with zero standard deviation
        std[std == 0] = 1
        return (x_train - mean) / std

    @abstractmethod
    def fit(self, data: np.ndarray) -> None:
        """
        Fit the model to the data.

        :param data: Training data
        :type data: np.ndarray
        """
        pass

    @abstractmethod
    def transform(self, data: np.ndarray) -> np.ndarray:
        """
        Transform the data using the fitted model.

        :param data: Data to transform
        :type data: np.ndarray
        :returns: Transformed data
        :rtype: np.ndarray
        """
        pass

    @abstractmethod
    def fit_transform(self, data: np.ndarray) -> np.ndarray:
        """
        Fit the model to the data and transform it.

        :param data: Training data
        :type data: np.ndarray
        :returns: Transformed data
        :rtype: np.ndarray
        """
        pass

    def save(self, file_path: str) -> None:
        """
        Save the fitted model to a file.

        :param file_path: Path to save the model to
        :type file_path: str
        :raises ValueError: If the model has not been fitted
        """
        if not self.is_fitted:
            raise ValueError(f"{self.__class__.__name__} model has not been fitted. Nothing to save.")
        joblib.dump(self.model, file_path)

    def load(self, file_path: str) -> None:
        """
        Load a model from a file.

        :param file_path: Path to load the model from
        :type file_path: str
        """
        self.model = joblib.load(file_path)


class PCAReducer(BaseReducer):
    """
    Dimensionality reduction using Principal Component Analysis (PCA).
    """

    def _check_is_fitted(self) -> bool:
        """Check if the PCA model has been fitted."""
        # Check for attributes that only exist after fitting
        if self.model is None:
            return False
        return hasattr(self.model, 'components_') and hasattr(self.model, 'mean_')

    def fit(self, data: np.ndarray) -> None:
        """
        Fit the PCA model to the data.

        :param data: Training data
        :type data: np.ndarray
        """
        self._validate_input(data)
        self.model = PCA(n_components=self.n_components)
        self.model.fit(data)

    def transform(self, data: np.ndarray) -> np.ndarray:
        """
        Transform the data using the fitted PCA model.

        :param data: Data to transform
        :type data: np.ndarray
        :returns: Transformed data
        :rtype: np.ndarray
        :raises ValueError: If the model has not been fitted
        """
        self._validate_input(data)
        if not self.is_fitted:
            raise ValueError("PCA model has not been fitted. Call fit() before transform().")
        return self.model.transform(data)

    def fit_transform(self, data: np.ndarray) -> np.ndarray:
        """
        Fit the PCA model to the data and transform it.

        :param data: Training data
        :type data: np.ndarray
        :returns: Transformed data
        :rtype: np.ndarray
        """
        self._validate_input(data)
        self.model = PCA(n_components=self.n_components)
        return self.model.fit_transform(data)

    def get_explained_variance_ratio(self) -> np.ndarray:
        """
        Get the amount of variance explained by each of the selected components.

        :returns: Percentage of variance explained by each of the selected components
        :rtype: np.ndarray
        :raises RuntimeError: If the model has not been fitted
        """
        if not self.is_fitted:
            raise RuntimeError("PCA model is not fitted yet. Call 'fit' with appropriate data.")
        return self.model.explained_variance_ratio_


class TruncationReducer(BaseReducer):
    """
    Simple dimensionality reduction by truncating vectors to their first n_components.
    Used as a fallback when other models aren't available to load.
    """

    def _check_is_fitted(self) -> bool:
        """
        TruncationReducer is always considered fitted as it doesn't require training.
        """
        return True

    def fit(self, data: np.ndarray) -> None:
        """
        No-op for TruncationReducer as it doesn't require fitting.

        :param data: Training data (ignored)
        :type data: np.ndarray
        """
        self._validate_input(data)
        # Verify that n_components is not greater than the dimension of the data
        if self.n_components > data.shape[1]:
            logger.warning(
                f"TruncationReducer: n_components ({self.n_components}) is greater than "
                f"the dimension of the data ({data.shape[1]}). Using {data.shape[1]} components instead."
            )
            self.n_components = min(self.n_components, data.shape[1])
        self.model = True  # Just a flag to indicate it's ready

    def transform(self, data: np.ndarray) -> np.ndarray:
        """
        Transform the data by truncating to the first n_components dimensions.

        :param data: Data to transform
        :type data: np.ndarray
        :returns: Truncated data
        :rtype: np.ndarray
        """
        self._validate_input(data)
        # Ensure n_components doesn't exceed the data dimensions
        n_dim = min(self.n_components, data.shape[1])
        return data[:, :n_dim]

    def fit_transform(self, data: np.ndarray) -> np.ndarray:
        """
        Fit and transform the data (just truncates to first n_components).

        :param data: Training data
        :type data: np.ndarray
        :returns: Truncated data
        :rtype: np.ndarray
        """
        self.fit(data)
        return self.transform(data)


class ReducerFactory:
    """
    Factory for creating and retrieving dimensionality reducers.
    """
    # Map of reducer types to their class implementations
    REDUCER_TYPES: Dict[str, Type[BaseReducer]] = {
        'pca': PCAReducer,
        'truncation': TruncationReducer
    }

    @classmethod
    def get_reducer(cls, reducer_type: str, n_components: int = 2, **kwargs) -> BaseReducer:
        """
        Get a reducer instance of the specified type.

        :param reducer_type: Type of reducer to create ('pca' or 'truncation')
        :type reducer_type: str
        :param n_components: Number of dimensions to reduce to
        :type n_components: int
        :param kwargs: Additional keyword arguments to pass to the reducer constructor
        :type kwargs: Dict[str, Any]
        :returns: Reducer instance
        :rtype: BaseReducer
        :raises ValueError: If the specified reducer type is not supported
        """
        reducer_type = reducer_type.lower()
        if reducer_type not in cls.REDUCER_TYPES:
            available_types = list(cls.REDUCER_TYPES.keys())
            raise ValueError(
                f"Unsupported reducer type: {reducer_type}. Available types: {available_types}"
            )

        return cls.REDUCER_TYPES[reducer_type](n_components=n_components, **kwargs)

    @classmethod
    def get_available_reducer(cls, reducer_types: List[str], model_paths: Dict[str, str],
                              n_components: int = 2, **kwargs) -> BaseReducer:
        """
        Try to load models in order of preference, falling back to TruncationReducer if none are available.

        :param reducer_types: List of reducer types to try, in order of preference
        :type reducer_types: List[str]
        :param model_paths: Dictionary mapping reducer types to file paths where models are stored
        :type model_paths: Dict[str, str]
        :param n_components: Number of dimensions to reduce to
        :type n_components: int
        :param kwargs: Additional keyword arguments to pass to the reducer constructor
        :type kwargs: Dict[str, Any]
        :returns: Reducer instance (loaded with model if available)
        :rtype: BaseReducer
        """
        for reducer_type in reducer_types:
            if reducer_type not in cls.REDUCER_TYPES:
                logger.warning(f"Unsupported reducer type: {reducer_type}. Skipping.")
                continue

            try:
                if reducer_type in model_paths:
                    reducer = cls.get_reducer(reducer_type, n_components, **kwargs)
                    reducer.load(model_paths[reducer_type])
                    logger.info(f"Successfully loaded {reducer_type} model from {model_paths[reducer_type]}")
                    return reducer
            except Exception as e:
                logger.warning(f"Failed to load {reducer_type} model: {str(e)}")

        # Fall back to TruncationReducer if no other reducers could be loaded
        logger.info("Falling back to TruncationReducer as no other models could be loaded")
        return cls.get_reducer('truncation', n_components, **kwargs)
