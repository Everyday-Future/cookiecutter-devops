# core/daos/embedding/clustering.py
import joblib
from sklearn.cluster import BisectingKMeans


class BisectingKMeansReducer:
    def __init__(self):
        self.model = None

    def fit(self, data, n_clusters=8, init='random', n_init=1, random_state=None, max_iter=300, verbose=0, tol=0.0001,
            copy_x=True, algorithm='lloyd', bisecting_strategy='biggest_inertia'):
        """Fit the Bisecting K-Means model to the data."""
        self.model = BisectingKMeans(
            n_clusters=n_clusters,
            init=init,
            n_init=n_init,
            random_state=random_state,
            max_iter=max_iter,
            verbose=verbose,
            tol=tol,
            copy_x=copy_x,
            algorithm=algorithm,
            bisecting_strategy=bisecting_strategy
        )
        self.model.fit(data)

    def predict(self, data):
        """Predict the closest cluster each sample in data belongs to."""
        if self.model is None:
            raise ValueError("Bisecting K-Means model has not been fitted. Call fit() before predict().")
        return self.model.predict(data)

    def fit_predict(self, data, n_clusters=8, init='random', n_init=1, random_state=None, max_iter=300, verbose=0,
                    tol=0.0001, copy_x=True, algorithm='lloyd', bisecting_strategy='biggest_inertia'):
        """Fit the Bisecting K-Means model to the data and predict the closest cluster each sample belongs to."""
        self.fit(data, n_clusters, init, n_init, random_state, max_iter, verbose, tol, copy_x, algorithm,
                 bisecting_strategy)
        return self.model.labels_

    def transform(self, data):
        """Transform the data to cluster-distance space."""
        if self.model is None:
            raise ValueError("Bisecting K-Means model has not been fitted. Call fit() before transform().")
        return self.model.transform(data)

    def save(self, file_path):
        """Save the fitted Bisecting K-Means model to a file."""
        if self.model is None:
            raise ValueError("Bisecting K-Means model has not been fitted. Nothing to save.")
        joblib.dump(self.model, file_path)

    def load(self, file_path):
        """Load a Bisecting K-Means model from a file."""
        self.model = joblib.load(file_path)
