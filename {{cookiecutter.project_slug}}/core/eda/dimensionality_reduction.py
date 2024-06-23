from sklearn.decomposition import PCA
from sklearn.model_selection import GridSearchCV
import numpy as np
import joblib
from typing import Optional, Union
from config import logger


class PCAAdapter:
    def __init__(self, n_components: Optional[Union[int, float, str]] = None):
        """
        Adapter for sklearn's PCA.

        Parameters:
        n_components (int, float, None or str): Number of components to keep.
        """
        self.n_components = n_components
        self.pca = PCA(n_components=n_components)
        self.is_fitted = False

    def fit(self, X: np.ndarray) -> None:
        """
        Fit the PCA model on the data.

        Parameters:
        X (np.ndarray): Training data, shape (n_samples, n_features)
        """
        self._validate_input(X)
        self.pca.fit(X)
        self.is_fitted = True
        logger.info("PCA model fitted with %d components.", self.pca.n_components_)

    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Apply dimensionality reduction to X.

        Parameters:
        X (np.ndarray): Data to transform, shape (n_samples, n_features)

        Returns:
        np.ndarray: Transformed data, shape (n_samples, n_components)
        """
        self._validate_input(X)
        if not self.is_fitted:
            raise RuntimeError("PCA model is not fitted yet. Call 'fit' with appropriate data.")
        return self.pca.transform(X)

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """
        Fit the model with X and apply the dimensionality reduction on X.

        Parameters:
        X (np.ndarray): Training data, shape (n_samples, n_features)

        Returns:
        np.ndarray: Transformed data, shape (n_samples, n_components)
        """
        self._validate_input(X)
        self.is_fitted = True
        return self.pca.fit_transform(X)

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        """
        Transform data back to its original space.

        Parameters:
        X (np.ndarray): Data in the transformed space, shape (n_samples, n_components)

        Returns:
        np.ndarray: Data in the original space, shape (n_samples, n_features)
        """
        self._validate_input(X)
        if not self.is_fitted:
            raise RuntimeError("PCA model is not fitted yet. Call 'fit' with appropriate data.")
        return self.pca.inverse_transform(X)

    def get_explained_variance_ratio(self) -> np.ndarray:
        """
        Get the amount of variance explained by each of the selected components.

        Returns:
        np.ndarray: Percentage of variance explained by each of the selected components.
        """
        if not self.is_fitted:
            raise RuntimeError("PCA model is not fitted yet. Call 'fit' with appropriate data.")
        return self.pca.explained_variance_ratio_

    def get_components(self) -> np.ndarray:
        """
        Get the principal axes in feature space.

        Returns:
        np.ndarray: Principal axes in feature space.
        """
        if not self.is_fitted:
            raise RuntimeError("PCA model is not fitted yet. Call 'fit' with appropriate data.")
        return self.pca.components_

    def save_model(self, file_path: str) -> None:
        """
        Save the PCA model to disk.

        Parameters:
        file_path (str): The path where to save the PCA model.
        """
        if not self.is_fitted:
            raise RuntimeError("PCA model is not fitted yet. Call 'fit' with appropriate data.")
        joblib.dump(self.pca, file_path)
        logger.info("PCA model saved to %s.", file_path)

    def load_model(self, file_path: str) -> None:
        """
        Load a PCA model from disk.

        Parameters:
        file_path (str): The path from where to load the PCA model.
        """
        self.pca = joblib.load(file_path)
        self.is_fitted = True
        logger.info("PCA model loaded from %s.", file_path)

    def tune_hyperparameters(self, X: np.ndarray, param_grid: dict, cv: int = 5) -> dict:
        """
        Perform hyperparameter tuning using GridSearchCV.

        Parameters:
        X (np.ndarray): Training data, shape (n_samples, n_features)
        param_grid (dict): Dictionary with parameters names (`str`) as keys and lists of parameter settings to try as values
        cv (int): Number of folds in cross-validation

        Returns:
        dict: The best parameters found in the search.
        """
        self._validate_input(X)
        grid_search = GridSearchCV(self.pca, param_grid, cv=cv)
        grid_search.fit(X)
        self.pca = grid_search.best_estimator_
        self.is_fitted = True
        logger.info("Hyperparameter tuning completed. Best parameters: %s", grid_search.best_params_)
        return grid_search.best_params_

    def _validate_input(self, X: np.ndarray) -> None:
        """
        Validate the input data.

        Parameters:
        X (np.ndarray): Data to validate.
        """
        if not isinstance(X, np.ndarray):
            raise ValueError("Input data should be a numpy array.")
        if X.ndim != 2:
            raise ValueError("Input data should be a 2D array.")

    def preprocess_data(self, X: np.ndarray) -> np.ndarray:
        """
        Preprocess the data (e.g., normalization).

        Parameters:
        X (np.ndarray): Data to preprocess.

        Returns:
        np.ndarray: Preprocessed data.
        """
        self._validate_input(X)
        mean = np.mean(X, axis=0)
        std = np.std(X, axis=0)
        return (X - mean) / std


# Example usage:
if __name__ == "__main__":
    # Sample data
    data = np.array([[2.5, 2.4],
                     [0.5, 0.7],
                     [2.2, 2.9],
                     [1.9, 2.2],
                     [3.1, 3.0],
                     [2.3, 2.7],
                     [2, 1.6],
                     [1, 1.1],
                     [1.5, 1.6],
                     [1.1, 0.9]])

    # Initialize PCA Adapter
    pca_adapter = PCAAdapter(n_components=2)

    # Preprocess the data
    preprocessed_data = pca_adapter.preprocess_data(data)

    # Fit and transform the data
    transformed_data = pca_adapter.fit_transform(preprocessed_data)

    print("Transformed Data:")
    print(transformed_data)

    # Inverse transform the data
    original_data = pca_adapter.inverse_transform(transformed_data)

    print("Original Data (reconstructed):")
    print(original_data)

    # Get explained variance ratio
    print("Explained Variance Ratio:")
    print(pca_adapter.get_explained_variance_ratio())

    # Get principal components
    print("Principal Components:")
    print(pca_adapter.get_components())

    # Save the model
    pca_adapter.save_model('pca_model.joblib')

    # Load the model
    pca_adapter.load_model('pca_model.joblib')

    # Hyperparameter tuning
    param_grid = {'n_components': [1, 2, 3]}
    best_params = pca_adapter.tune_hyperparameters(preprocessed_data, param_grid)
    print("Best Parameters:")
    print(best_params)
