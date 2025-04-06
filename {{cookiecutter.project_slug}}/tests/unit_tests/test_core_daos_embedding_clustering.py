import pytest
import numpy as np
import os
from core.daos.embedding.clustering import BisectingKMeansReducer


@pytest.fixture
def sample_data():
    return np.random.rand(100, 768)  # 100 samples with 768 features each


def test_fit(sample_data):
    bkmeans = BisectingKMeansReducer()
    bkmeans.fit(sample_data, n_clusters=5)
    assert bkmeans.model is not None
    assert len(bkmeans.model.cluster_centers_) == 5


def test_predict(sample_data):
    bkmeans = BisectingKMeansReducer()
    bkmeans.fit(sample_data, n_clusters=5)
    predictions = bkmeans.predict(sample_data)
    assert len(predictions) == len(sample_data)


def test_fit_predict(sample_data):
    bkmeans = BisectingKMeansReducer()
    labels = bkmeans.fit_predict(sample_data, n_clusters=5)
    assert len(labels) == len(sample_data)
    assert len(set(labels)) == 5


def test_transform(sample_data):
    bkmeans = BisectingKMeansReducer()
    bkmeans.fit(sample_data, n_clusters=5)
    transformed_data = bkmeans.transform(sample_data)
    assert transformed_data.shape == (100, 5)


def test_save_and_load(sample_data):
    bkmeans = BisectingKMeansReducer()
    bkmeans.fit(sample_data, n_clusters=5)
    bkmeans.save('bkmeans_model.joblib')
    # Ensure the file is created
    assert os.path.exists('bkmeans_model.joblib')
    # Load the model
    loaded_bkmeans = BisectingKMeansReducer()
    loaded_bkmeans.load('bkmeans_model.joblib')
    # Ensure the model was loaded correctly
    assert loaded_bkmeans.model is not None
    # Predict with the loaded model
    new_data = np.random.rand(10, 768)  # 10 new samples with 768 features each
    new_predictions = loaded_bkmeans.predict(new_data)
    assert len(new_predictions) == len(new_data)
    # Clean up
    os.remove('bkmeans_model.joblib')


def test_predict_without_fit(sample_data):
    bkmeans = BisectingKMeansReducer()
    try:
        bkmeans.predict(sample_data)
        assert False
    except ValueError:
        pass
