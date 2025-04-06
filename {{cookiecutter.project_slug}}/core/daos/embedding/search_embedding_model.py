# core/daos/embedding/search_embedding_model.py
import os
import joblib
import numpy as np
import pandas as pd
from typing import List, Optional, Tuple
from sentence_transformers import SentenceTransformer
from config import Config
from core.daos.embedding.dimensionality_reduction import PCAReducer, BaseReducer, ReducerFactory


class SearchEmbeddingModel:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', reducer: Optional[BaseReducer] = None):
        """
        Initialize with a specific model and optional dimensionality reducer.

        Args:
            model_name (str): Name of the SentenceTransformer model to use
            reducer (BaseReducer): Optional dimensionality reduction model (e.g., PCAReducer)
        """
        self.model_name = model_name
        self.reducer = reducer
        self._load_model()

    def _load_model(self):
        """Load the sentence transformer model."""
        print(f"Loading model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        print(f"Model loaded. Vector dimension: {self.model.get_sentence_embedding_dimension()}")

    def get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding for a single text string.

        Args:
            text (str): The text to encode

        Returns:
            np.ndarray: The embedding vector (dimensionality reduced if reducer is fitted)

        Raises:
            ValueError: If input is not a non-empty string
        """
        if not text or not isinstance(text, str):
            raise ValueError("Input must be a non-empty string")

        # Generate embedding
        embedding = self.model.encode(text)
        # Convert to numpy array if it's a tensor
        if hasattr(embedding, 'numpy'):
            embedding = embedding.numpy()
        elif hasattr(embedding, 'detach'):
            embedding = embedding.detach().numpy()

        # Apply dimensionality reduction if applicable
        if self.reducer is not None and self.reducer.is_fitted:
            # Reshape to 2D for the reducer
            embedding_2d = embedding.reshape(1, -1)
            reduced = self.reducer.transform(embedding_2d)
            return reduced[0]  # Return as 1D array
        else:
            # If no reducer is available, truncate to the configured dimensions
            return embedding[:Config.SEARCH_VECTOR_DIMS]

    def fit_reducer(self, embeddings: np.ndarray) -> None:
        """
        Fit dimensionality reducer on a set of embeddings.

        Args:
            embeddings (np.ndarray): The embeddings to fit the reducer on

        Raises:
            ValueError: If embeddings have incorrect format or reducer is None
        """
        if self.reducer is None:
            print("Dimensionality reduction is disabled (reducer is None)")
            return

        if not isinstance(embeddings, np.ndarray):
            raise ValueError("Embeddings must be a numpy array")

        if embeddings.ndim != 2:
            raise ValueError("Embeddings must be a 2D array")

        original_dim = embeddings.shape[1]
        target_dim = self.reducer.n_components

        if target_dim > original_dim:
            print(f"Warning: n_components ({target_dim}) is greater than "
                  f"the dimension of the embeddings ({original_dim}). "
                  f"Using {original_dim} components instead.")
            # Update the reducer's n_components
            self.reducer.n_components = min(target_dim, original_dim)

        print(f"Fitting dimensionality reducer with {self.reducer.n_components} "
              f"components on {len(embeddings)} embeddings...")
        self.reducer.fit(embeddings)

        # Print information about variance if it's a PCA reducer
        if isinstance(self.reducer, PCAReducer) and hasattr(self.reducer, 'get_explained_variance_ratio'):
            explained_variance = self.reducer.get_explained_variance_ratio()
            cumulative_variance = np.cumsum(explained_variance)
            print(f"Total variance explained by {self.reducer.n_components} components: "
                  f"{cumulative_variance[-1] * 100:.2f}%")

    def get_embeddings(self, texts: List[str], batch_size: int = 32,
                       show_progress: bool = True, fit_reducer: bool = False) -> np.ndarray:
        """
        Generate embeddings for a list of texts and optionally reduce their dimensionality.

        Args:
            texts (List[str]): The texts to generate embeddings for
            batch_size (int): Batch size for encoding
            show_progress (bool): Whether to show a progress bar
            fit_reducer (bool): Whether to fit the reducer on these embeddings if not already fitted

        Returns:
            np.ndarray: The embeddings (reduced if reducer is fitted or fit_reducer=True)

        Raises:
            ValueError: If texts is not a non-empty list of strings
        """
        if not texts:
            raise ValueError("Input must be a non-empty list of strings")

        # Generate embeddings
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress
        )

        # Fit reducer if requested and not already fitted
        if fit_reducer and self.reducer is not None and not self.reducer.is_fitted:
            self.fit_reducer(embeddings)

        # Apply dimensionality reduction if reducer is fitted
        if self.reducer is not None and self.reducer.is_fitted:
            print(f"Reducing dimensionality from {embeddings.shape[1]} to {self.reducer.n_components}...")
            reduced_embeddings = self.reducer.transform(embeddings)
            return reduced_embeddings

        return embeddings

    def save(self, filepath: str) -> None:
        """
        Save the EmbeddingsGenerator instance to a file, including the reducer if present.

        Args:
            filepath (str): Path to save the model to
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        # Build state dictionary
        state_dict = {
            'model_name': self.model_name,
            'has_reducer': self.reducer is not None,
            'reducer_type': type(self.reducer).__name__ if self.reducer else None,
            'reducer_n_components': self.reducer.n_components if self.reducer else None,
            'reducer': self.reducer if self.reducer else None
        }

        # Save the state dictionary
        joblib.dump(state_dict, filepath)
        print(f"EmbeddingsGenerator saved to {filepath}")

    @classmethod
    def load(cls, filepath: str) -> 'SearchEmbeddingModel':
        """
        Load an EmbeddingsGenerator instance from a file.

        Args:
            filepath (str): Path to load the model from

        Returns:
            SearchEmbeddingModel: The loaded instance

        Raises:
            FileNotFoundError: If the file doesn't exist
            RuntimeError: If there's an error loading the model
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        try:
            # Load the state dictionary
            state_dict = joblib.load(filepath)

            # Extract model name and create instance
            model_name = state_dict.get('model_name')

            # Create a new instance with the saved model name
            instance = cls(model_name=model_name, reducer=None)

            # Restore reducer if it was saved
            if state_dict.get('has_reducer', False) and state_dict.get('reducer') is not None:
                instance.reducer = state_dict['reducer']
                print(f"Restored {state_dict['reducer_type']} reducer with "
                      f"{instance.reducer.n_components} components")

            return instance

        except Exception as e:
            raise RuntimeError(f"Error loading EmbeddingsGenerator: {str(e)}")

    @classmethod
    def load_for_search(
            cls, model_name: str = 'all-MiniLM-L6-v2', dimensions: int = 30, model_path=None
    ) -> 'SearchEmbeddingModel':
        """
        Load an EmbeddingsGenerator configured for search with appropriate fallbacks.

        Args:
            model_name (str): Name of the SentenceTransformer model to use
            dimensions (int): Target dimensions for embeddings
            model_path (str): Path to load the pre-trained embedding model

        Returns:
            SearchEmbeddingModel: Configured generator instance
        """

        # Create reducer with appropriate fallback
        try:
            # Try to load PCA reducer
            reducer = ReducerFactory.get_reducer('pca', n_components=dimensions)
            model_path = model_path or os.path.join(Config.PIPELINE_DIR, "models", "search_embedding.joblib")

            if os.path.exists(model_path):
                reducer.load(model_path)
                print(f"Successfully loaded PCA reducer from {model_path}")
            else:
                # Use truncation reducer if PCA model isn't available
                reducer = ReducerFactory.get_reducer('truncation', n_components=dimensions)
                print(f"PCA model not found at {model_path}, using TruncationReducer instead")
        except Exception as e:
            print(f"Error loading reducer: {str(e)}. Using TruncationReducer instead.")
            reducer = ReducerFactory.get_reducer('truncation', n_components=dimensions)

        # Initialize the generator with the model and reducer
        return cls(model_name=model_name, reducer=reducer)

    @classmethod
    def from_df(
            cls,
            target_df: pd.DataFrame,
            text_col: str,
            n_components: int = 30,
            model_name: str = 'all-MiniLM-L6-v2'
    ) -> Tuple['SearchEmbeddingModel', pd.DataFrame]:
        # Initialize the embedding model with PCA reducer
        print("Initializing embedding model with PCA dimensionality reduction...")
        reducer = PCAReducer(n_components=n_components)
        embedding_model = cls(model_name=model_name, reducer=reducer)
        # Get embeddings for the summary results
        print(f"Generating embeddings for {len(target_df)} summaries...")
        summary_texts = target_df[text_col].tolist()
        # Get the full embeddings first (without reduction)
        full_embeddings = embedding_model.get_embeddings(
            texts=summary_texts,
            batch_size=16,
            show_progress=True,
            fit_reducer=False
        )
        # Fit the reducer on the embeddings and get reduced embeddings
        print("Fitting PCA reducer and generating reduced embeddings...")
        embedding_model.fit_reducer(full_embeddings)
        reduced_embeddings = embedding_model.reducer.transform(full_embeddings)
        # Add the full and reduced embeddings to the dataframe
        target_df['full_embedding'] = list(full_embeddings)
        target_df['reduced_embedding'] = list(reduced_embeddings)
        return embedding_model, target_df

    @staticmethod
    def export_for_tf_projector(
            df: pd.DataFrame,
            embedding_col: str,
            metadata_cols: list,
            output_dir: str,
            vectors_filename: str = 'vectors.tsv',
            metadata_filename: str = 'metadata.tsv'
    ):
        """Export embeddings to TSV files for TensorFlow Projector"""
        # Create output directory if needed
        os.makedirs(output_dir, exist_ok=True)
        # Create vectors TSV file
        vectors_path = os.path.join(output_dir, vectors_filename)
        with open(vectors_path, 'w') as f:
            for embedding in df[embedding_col]:
                # Convert each vector to tab-separated string
                vector_str = '\t'.join(str(value) for value in embedding)
                f.write(f"{vector_str}\n")
        # Create metadata TSV file
        metadata_path = os.path.join(output_dir, metadata_filename)
        # Extract metadata columns to a new dataframe
        metadata_df = df[metadata_cols].copy()
        # Clean metadata values - remove tabs and newlines
        for col in metadata_cols:
            if metadata_df[col].dtype == object:  # Only process string columns
                metadata_df[col] = metadata_df[col].astype(str).str.replace('\t', ' ').str.replace('\n', ' ')
        # Save metadata to TSV
        metadata_df.to_csv(metadata_path, sep='\t', index=False)
        print(f"Exported {len(df)} vectors to {vectors_path}")
        print(f"Exported metadata with columns {metadata_cols} to {metadata_path}")
        return vectors_path, metadata_path
