import pytest
from unittest.mock import patch
from typing import List
from core.daos.llms.agent import InferenceModels, Config


class MockConfig:
    DEFAULT_LLMS_FAST = ["model//fast1", "model//fast2"]
    DEFAULT_LLMS_SMALL = ["model//small1", "model//small2"]
    DEFAULT_LLMS_MED = ["model//med1", "model//med2"]
    DEFAULT_LLMS_LARGE = ["model//large1", "model//large2"]
    DEFAULT_LLMS_HUGE = ["model//huge1", "model//huge2"]
    DEFAULT_LLMS_IMAGE_PARSE = ["model//image1"]
    DEFAULT_EMBEDDING_MODEL = "model//embed1"
    DEFAULT_LLMS_SAFETY = ["model//safety1"]
    DEFAULT_LLMS_UNCENSORED = ["model//uncensored1"]


@pytest.fixture
def mock_config():
    with patch('core.daos.llms.agent.Config', MockConfig):
        yield MockConfig


class TestInferenceModelsUnit:
    """Unit tests for InferenceModels enum class"""

    def test_str_representation(self):
        """Test string representation of enum values"""
        assert str(InferenceModels.FAST) == 'fast'
        assert str(InferenceModels.HUGE) == 'huge'
        assert str(InferenceModels.IMAGE) == 'image'

    def test_get_difficulty_order(self):
        """Test difficulty order is correct and complete"""
        order = InferenceModels.FAST._get_difficulty_order()
        expected = [
            InferenceModels.FAST,
            InferenceModels.SMALL,
            InferenceModels.MED,
            InferenceModels.LARGE,
            InferenceModels.HUGE
        ]
        assert order == expected

    @pytest.mark.parametrize("min_diff,max_diff,target_diff,expected_count", [
        (None, None, None, 5),  # All difficulties
        (InferenceModels.MED, None, None, 3),  # Med and above
        (None, InferenceModels.MED, None, 3),  # Up to Med
        (InferenceModels.SMALL, InferenceModels.LARGE, None, 4),  # Range
        (None, None, InferenceModels.MED, 1),  # Specific target
    ])
    def test_filter_models_by_difficulty(self, min_diff, max_diff, target_diff, expected_count):
        """Test difficulty filtering with various parameters"""
        result = InferenceModels.FAST._filter_models_by_difficulty(min_diff, max_diff, target_diff)
        assert len(result) == expected_count

    def test_filter_models_invalid_difficulty(self):
        """Test filtering with invalid difficulty levels"""
        # Test with IMAGE as min_difficulty
        try:
            result = InferenceModels.FAST._filter_models_by_difficulty(InferenceModels.IMAGE,
                                                                       None,
                                                                       None)
            raise ValueError('invalid model filter should raise Assertion Error')
        except AssertionError:
            pass
        # Test with IMAGE as max_difficulty
        try:
            result = InferenceModels.FAST._filter_models_by_difficulty(None,
                                                                       InferenceModels.IMAGE,
                                                                       None)
            raise ValueError('invalid model filter should raise Assertion Error')
        except AssertionError:
            pass
        # Test with IMAGE as target_difficulty
        try:
            result = InferenceModels.FAST._filter_models_by_difficulty(None,
                                                                       None,
                                                                       InferenceModels.IMAGE)
            raise ValueError('invalid model filter should raise Assertion Error')
        except AssertionError:
            pass

    @pytest.mark.parametrize("difficulty", [
        InferenceModels.FAST,
        InferenceModels.SMALL,
        InferenceModels.MED,
        InferenceModels.LARGE,
        InferenceModels.HUGE,
    ])
    def test_get_model_list(self, mock_config, difficulty):
        """Test model list retrieval for each difficulty level"""
        models = difficulty._get_model_list(difficulty.value)
        assert isinstance(models, list)
        assert all("//" in model for model in models)

    def test_to_list_deduplication(self, mock_config):
        """Test that to_list properly deduplicates models"""
        # Add some duplicate models in the mock
        with patch.object(MockConfig, 'DEFAULT_LLMS_MED', MockConfig.DEFAULT_LLMS_SMALL):
            models = InferenceModels.FAST.to_list()
            assert len(models) == len(set(models))  # No duplicates

    @pytest.mark.parametrize("count", [1, 3, 5])
    def test_select_random_list(self, mock_config, count):
        """Test random selection with replacement"""
        models = InferenceModels.FAST.select_random_list(count)
        assert len(models) == count
        assert all(isinstance(model, str) for model in models)
        assert all("//" in model for model in models)

    def test_select_random_list_invalid_count(self):
        """Test random selection with invalid count"""
        with pytest.raises(ValueError):
            InferenceModels.FAST.select_random_list(0)
        with pytest.raises(ValueError):
            InferenceModels.FAST.select_random_list(-1)

    def test_get_model_returns_first(self, mock_config):
        """Test that get_model returns the first model from the list"""
        model = InferenceModels.FAST.default_model
        assert model == MockConfig.DEFAULT_LLMS_FAST[0]


class TestInferenceModelsIntegration:
    """Integration tests for InferenceModels with actual Config"""

    def _validate_model_string(self, model: str) -> bool:
        """Helper to validate model string format"""
        return isinstance(model, str) and "//" in model

    def _validate_model_list(self, models: List[str]) -> bool:
        """Helper to validate list of model strings"""
        return isinstance(models, list) and all(self._validate_model_string(m) for m in models)

    @pytest.mark.integration
    def test_config_variables_validity(self):
        """Test that all Config variables are properly formatted"""
        assert self._validate_model_list(Config.DEFAULT_LLMS_FAST)
        assert self._validate_model_list(Config.DEFAULT_LLMS_SMALL)
        assert self._validate_model_list(Config.DEFAULT_LLMS_MED)
        assert self._validate_model_list(Config.DEFAULT_LLMS_LARGE)
        assert self._validate_model_list(Config.DEFAULT_LLMS_HUGE)
        assert self._validate_model_list(Config.DEFAULT_LLMS_IMAGE_PARSE)
        assert self._validate_model_string(Config.DEFAULT_EMBEDDING_MODEL)
        assert self._validate_model_list(Config.DEFAULT_LLMS_SAFETY)
        assert self._validate_model_list(Config.DEFAULT_LLMS_UNCENSORED)
