""" Compiler for all .env secrets """

import os
import sys
import json
from jinja2 import Environment, BaseLoader, StrictUndefined
from config import Config


def build(local_config='docker'):
    global_config = Config()
    with open(os.path.join(global_config.PROJECT_DIR, 'secret--template.env'), 'r') as fp:
        template_text = fp.read()
    with open(os.path.join(global_config.PROJECT_DIR, 'secret--template-values.env'), 'r') as fp:
        configs = json.load(fp)
    template = Environment(loader=BaseLoader(), trim_blocks=True, lstrip_blocks=True,
                           undefined=StrictUndefined).from_string(template_text)
    for env_name, values in configs.items():
        values.update({'version': global_config.VERSION})
        with open(os.path.join(global_config.PROJECT_DIR, f'secret-{env_name}.env'), 'w') as fp:
            fp.write(template.render(**values))
    local_configs = configs[local_config]
    local_configs.update({'version': global_config.VERSION})
    # Create the local local.env file
    with open(os.path.join(global_config.PROJECT_DIR, 'local.env'), 'w') as fp:
        fp.write(template.render(**local_configs))
    print(f'\n\n\n\n-------------------------------------------------------')
    print(f'Rebuilt local secrets for MODE == {local_config}')
    print(f'-------------------------------------------------------\n\n')


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_config = sys.argv[1]
    else:
        target_config = 'docker'
    # Build all the .env files from the template and secrets
    build(target_config)
