""" Compiler for all .env secrets """

import os
import sys
import json
from jinja2 import Environment, BaseLoader, StrictUndefined


def build(stage='docker'):
    with open('config.json', 'r') as fp:
        version = json.load(fp=fp)['version']
    project_dir = os.path.dirname(os.path.dirname(__file__))
    with open(os.path.join(project_dir, 'secret-template.env'), 'r') as fp:
        template_text = fp.read()
    with open(os.path.join(project_dir, 'secret-template-values.env'), 'r') as fp:
        configs = json.load(fp)
    template = Environment(loader=BaseLoader(), trim_blocks=True, lstrip_blocks=True,
                           undefined=StrictUndefined).from_string(template_text)
    for env_name, values in configs.items():
        values.update({'version': version})
        with open(os.path.join(project_dir, f'secret-{env_name}.env'), 'w') as fp:
            fp.write(template.render(**values))
    # Create the local integration.env file
    with open(os.path.join(project_dir, 'integration.env'), 'w') as fp:
        api_configs = configs['api-' + stage]
        api_configs.update({'version': version})
        fp.write(template.render(**api_configs))
    with open(os.path.join(project_dir, "frontend/docker.env"), 'w') as fp:
        frontend_configs = configs['frontend-' + stage]
        frontend_configs.update({'version': version})
        fp.write(template.render(**frontend_configs))
    with open(os.path.join(project_dir, "frontend/.env"), 'w') as fp:
        frontend_configs = configs['frontend-' + stage]
        frontend_configs.update({'version': version})
        fp.write(template.render(**frontend_configs))
    print(f'\n\n\n\n-------------------------------------------------------')
    print(f'Rebuilt local secrets for MODE == {stage}')
    print(f'-------------------------------------------------------\n\n')


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_config = sys.argv[1]
    else:
        target_config = 'docker'
    # Build all the .env files from the template and secrets
    build(target_config)
