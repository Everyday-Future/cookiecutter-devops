#!/usr/bin/env python
import os
import stat

PROJECT_DIRECTORY = os.path.realpath(os.path.curdir)


def remove_file(filepath):
    os.remove(os.path.join(PROJECT_DIRECTORY, filepath))


if __name__ == '__main__':

    if 'no' in '{{ cookiecutter.command_line_interface|lower }}':
        cli_file = os.path.join('{{ cookiecutter.project_slug }}', 'cli.py')
        remove_file(cli_file)

    if 'Not open source' == '{{ cookiecutter.open_source_license }}':
        remove_file('LICENSE')

    # Create secret envs
    os.rename(os.path.join(PROJECT_DIRECTORY, 'secret--template.env.txt'),
              os.path.join(PROJECT_DIRECTORY, 'secret--template.env'))
    os.rename(os.path.join(PROJECT_DIRECTORY, 'secret--template-values.env.txt'),
              os.path.join(PROJECT_DIRECTORY, 'secret--template-values.env'))

    # Convert shell scripts for Windows
    shell_scripts = [os.path.join(PROJECT_DIRECTORY, '.__run_cli.sh'),
                     os.path.join(PROJECT_DIRECTORY, 'boot.sh'),
                     os.path.join(PROJECT_DIRECTORY, 'host', 'test_all.sh'),
                     os.path.join(PROJECT_DIRECTORY, 'host', 'test_loop.sh')]
    for shell_script in shell_scripts:
        with open(shell_script, "r") as fin:
            lines = []
            for line in fin:
                lines.append(line.replace('\r\n', '\n'))
        with open(shell_script, "w") as fout:
            fout.writelines(lines)

    # Make shell scripts executable
    for shell_script in shell_scripts:
        st = os.stat(shell_script)
        os.chmod(shell_script, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

