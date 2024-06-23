import os
import pytest
from config import Config
from core.adapters.llms.inference import _AnyscaleAgent
from core.adapters.llms.fine_tune import AnyscaleFineTuning


def test_fine_tune_data():
    test_fpath = os.path.join(Config.TEST_ASSETS_DIR, 'example-valid.jsonl')
    assert os.path.isfile(test_fpath)
    assert AnyscaleFineTuning.check_training_data_is_valid(dataset_fpath=test_fpath)


def test_list_files():
    assert isinstance(AnyscaleFineTuning.list_files(), list)


def test_upload_file():
    test_file = 'example-valid.jsonl'
    test_fpath = os.path.join(Config.TEST_ASSETS_DIR, test_file)
    # Check for file
    uploaded_file_id = AnyscaleFineTuning.get_uploaded_file_id(file_name=test_file)
    # If file is present, delete it
    if uploaded_file_id is not None:
        AnyscaleFineTuning.delete_file(uploaded_file_id)
    # Upload files
    file_id = AnyscaleFineTuning.upload_file(file_path=test_fpath)
    # List files to check for it
    assert AnyscaleFineTuning.get_uploaded_file_id(file_name=test_file) is not None
    # Get file contents
    assert len(AnyscaleFineTuning.get_file_contents(file_id=file_id)) > 2000
    # Delete file
    assert AnyscaleFineTuning.delete_file(file_id=file_id) is not None
    # List files to confirm
    assert file_id not in AnyscaleFineTuning.list_files()


@pytest.mark.skip('This costs $5 every time it is run')
def test_fine_tuning():
    model_id = AnyscaleFineTuning.create_fine_tuning_job(model="mistralai/Mistral-7B-Instruct-v0.1",
                                                         training_file='file_vx2a8bni6tkdlepy829ewbsy69',
                                                         validation_file='file_th4u41daywatpskuwuaik3ugb2')
    print('model_id', model_id)
    resp = AnyscaleFineTuning.list_fine_tuning_jobs()
    print('resp2', resp)
