"""

Fine-Tuning

Anyscale - $5 base charge and a few $ per M token for a fine-tuned Mixtral or Llama.

"""
import json
import requests
from config import Config
import openai


class DataFormatError(Exception):
    pass


class AnyscaleFineTuning:
    """
    https://docs.endpoints.anyscale.com/fine_tune/fine_tuning_api
    """
    api_key = Config.ANYSCALE_API_KEY
    base_url = Config.ANYSCALE_BASE_URL
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    client = openai.OpenAI(
        base_url=Config.ANYSCALE_BASE_URL,
        api_key=Config.ANYSCALE_API_KEY
    )

    @classmethod
    def check_training_data_is_valid(cls, dataset_fpath):
        with open(dataset_fpath, 'r', encoding='utf-8') as f:
            items = [json.loads(line) for line in f]
        try:
            for line_num, batch in enumerate(items):
                prefix = f"Error in line #{line_num + 1}: "
                if not isinstance(batch, dict):
                    raise DataFormatError(
                        f"{prefix}Each line in the provided data should be a dictionary"
                    )
                if "messages" not in batch:
                    raise DataFormatError(
                        f"{prefix}Each line in the provided data should have a 'messages' key"
                    )
                if not isinstance(batch["messages"], list):
                    raise DataFormatError(
                        f"{prefix}Each line in the provided data should have a 'messages' key with a list of messages"
                    )
                messages = batch["messages"]
                if not any(message.get("role", None) == "assistant" for message in messages):
                    raise DataFormatError(
                        f"{prefix}Each message list should have at least one message with role 'assistant'"
                    )
                for message_num, message in enumerate(messages):
                    prefix = f"Error in line #{line_num + 1}, message #{message_num + 1}: "
                    if "role" not in message or "content" not in message:
                        raise DataFormatError(
                            f"{prefix}Each message should have a 'role' and 'content' key"
                        )
                    if any(k not in ("role", "content", "name") for k in message):
                        raise DataFormatError(
                            f"{prefix}Each message should only have 'role', 'content', and 'name' keys, "
                            f"any other key is not allowed"
                        )
                    if message.get("role", None) not in ("system", "user", "assistant"):
                        raise DataFormatError(
                            f"{prefix}Each message should have a valid role (system, user, or assistant)"
                        )
        except DataFormatError:
            return False
        return True

    @staticmethod
    def convert_to_training_format(data, system_prompt, user_prompt_template, assistant_prompt_template):
        training_data = []
        for row in data:
            training_data.append({
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt_template.format(**row)},
                    {'role': 'assistant', 'content': assistant_prompt_template.format(**row)}
                ]
            })
        return training_data

    @staticmethod
    def save_to_jsonl(filename, data):
        with open(filename, 'w') as f:
            for item in data:
                f.write(json.dumps(item) + '\n')

    @classmethod
    def upload_file(cls, file_path, purpose="fine-tune"):
        if purpose == "fine-tune":
            return cls.client.files.create(
              file=open(file_path, "rb"),
              purpose="fine-tune",
            ).id
        else:
            return cls.client.files.create(
              file=open(file_path, "rb"),
              purpose="assistants",
            ).id

    @classmethod
    def list_files(cls):
        url = f'{cls.base_url}/files'
        response = requests.get(url, headers=cls.headers)
        return response.json()['data']

    @classmethod
    def get_uploaded_file_id(cls, file_name):
        uploaded_files = [f for f in cls.list_files() if f['filename'] == file_name]
        if len(uploaded_files) > 0:
            return uploaded_files[0]['id']
        else:
            return None

    @classmethod
    def is_file_uploaded(cls, file_name):
        return cls.get_uploaded_file_id(file_name=file_name) is not None

    @classmethod
    def get_file(cls, file_id):
        url = f'{cls.base_url}/files/{file_id}'
        response = requests.get(url, headers=cls.headers)
        return response.json()

    @classmethod
    def get_file_contents(cls, file_id):
        url = f'{cls.base_url}/files/{file_id}/content'
        response = requests.get(url, headers=cls.headers)
        return response.content.decode('utf-8')

    @classmethod
    def delete_file(cls, file_id):
        url = f'{cls.base_url}/files/{file_id}'
        response = requests.delete(url, headers=cls.headers)
        resp = response.json()
        if 'id' in resp:
            return resp['id']
        else:
            return None

    @classmethod
    def create_fine_tuning_job(cls, model, training_file, validation_file=None, hyperparameters=None):
        url = f'{cls.base_url}/fine_tuning/jobs'
        payload = {
            'model': model,
            'training_file': training_file
        }
        if validation_file:
            payload['validation_file'] = validation_file
        if hyperparameters:
            payload['hyperparameters'] = hyperparameters
        response = requests.post(url, json=payload, headers=cls.headers)
        return response.json()['fine_tuned_model']

    @classmethod
    def get_fine_tuning_job(cls, fine_tuning_job_id):
        url = f'{cls.base_url}/fine_tuning/jobs/{fine_tuning_job_id}'
        response = requests.get(url, headers=cls.headers)
        return response.json()

    @classmethod
    def list_fine_tuning_jobs(cls, after=None, limit=20):
        url = f'{cls.base_url}/fine_tuning/jobs'
        params = {}
        if after:
            params['after'] = after
        if limit:
            params['limit'] = limit
        response = requests.get(url, params=params, headers=cls.headers)
        return response.json()

    @classmethod
    def cancel_fine_tuning_job(cls, fine_tuning_job_id):
        url = f'{cls.base_url}/fine_tuning/jobs/{fine_tuning_job_id}/cancel'
        response = requests.post(url, headers=cls.headers)
        return response.json()
