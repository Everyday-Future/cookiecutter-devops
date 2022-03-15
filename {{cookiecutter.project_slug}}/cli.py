import os
import time
import click
import subprocess
import requests
from config import Version, Config


local_server_url = Config.SERVER_URL
staging_server_url = Config.STAGING_URL


class SubProcessor:
    """
    Run shell subprocesses with python
    """

    @staticmethod
    def docker_down():
        subprocess.run('docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml down --remove-orphans')

    @staticmethod
    def upgrade_db():
        subprocess.run('docker-compose run -e FLASK_DEBUG=1 -p 5008:5008 api flask db upgrade')

    @staticmethod
    def docker_up():
        subprocess.run('docker-compose up')

    @staticmethod
    def docker_up_integration():
        subprocess.run('docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml up')

    @classmethod
    def docker_build(cls, force_rm=False):
        cls.docker_down()
        force_rm_str = ""
        if force_rm is True:
            force_rm_str = '--force-rm'
        subprocess.run(f'docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml '
                       f'build --parallel {force_rm_str}')

    @classmethod
    def debug_up(cls):
        cls.docker_down()
        cls.upgrade_db()
        subprocess.run('docker-compose -f docker-compose.yaml '
                       'run -e FLASK_DEBUG=1 -e SERVER_NAME=localhost:5000 -e CLIENT_HOST=localhost '
                       '-e CLIENT_PORT=5005 -e USE_HTTPS=False -p 5000:5000 '
                       'api flask run --host=0.0.0.0 --port=5000')

    @classmethod
    def debug_mobile_up(cls):
        cls.docker_down()
        cls.upgrade_db()
        subprocess.run('docker-compose -f docker-compose.yaml '
                       'run -e FLASK_DEBUG=1 -e SERVER_NAME=192.168.1.7:5008 '
                       '-e CLIENT_SERVER_NAME=192.168.1.7:5005 -e PORT=5008 -e USE_HTTPS=False -p 5008:5008 '
                       'api flask run --host=0.0.0.0 --port=5008')

    @classmethod
    def debug_svelte(cls, do_build=False):
        cls.docker_down()
        cls.upgrade_db()
        if do_build is True:
            subprocess.run(f'docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml '
                           f'build --force-rm --parallel ')
        subprocess.run('docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml up')

    @classmethod
    def storybook_up(cls, do_build=False):
        cls.docker_down()
        cls.upgrade_db()
        if do_build is True:
            subprocess.run(f'docker-compose -f docker-compose.yaml -f docker-compose.storybook.yaml '
                           f'build --force-rm --parallel ')
        subprocess.run('docker-compose -f docker-compose.yaml -f docker-compose.storybook.yaml up')

    @staticmethod
    def wait_for_server_up(target_url, max_timeout=300):
        """
        Try to hit a url and hang until the request stops timing out or max_timeout is reached.
        """
        start_time = time.time()
        while True:
            try:
                requests.get(target_url, timeout=5)
                return
            except requests.exceptions.Timeout:
                if (time.time() - start_time) > max_timeout:
                    return
                else:
                    pass

    @staticmethod
    def wait_for_version_number(target_url, target_version, max_timeout=300):
        """
        Wait for a server to answer with a version number in a json packet
        to indicate that a new verison has been pushed.

        This is used to trigger acceptance tests after a git tag/push macro.
        """
        start_time = time.time()
        while True:
            try:
                reply = requests.get(target_url, timeout=5)
                if reply.json().get('version') == target_version:
                    return
                elif (time.time() - start_time) > max_timeout:
                    return
            except requests.exceptions.Timeout:
                if (time.time() - start_time) > max_timeout:
                    return
                else:
                    pass

    @staticmethod
    def git_commit(message):
        """
        bump the version number and tag in git with it
        :param message: The message to add to the commit
        """
        subprocess.run(f'git add .')
        subprocess.run(f'git commit -m "{message}"')

    @staticmethod
    def git_bump(how, message, do_commit=True, do_push=True):
        """
        bump the version number and tag in git with it
        :param how: 'minor' or 'patch' for the version number column to bump.
        :param message: The message to add to a commit or tag the version with
        :param do_commit: commit the current changes before tagging
        :param do_push: push the tag to origin
        """
        ver = Version()
        ver.bump(how=how)
        ver_str = ver.version
        # Add the version, date, and message to the history.rst doc
        ver.append_history(ver_str, message)
        # commit if specified
        if do_commit is True:
            SubProcessor.git_commit(message=message)
        subprocess.run(f'git tag -a v{ver_str} -m "{message}"')
        # push if specified
        if do_push is True:
            subprocess.run(f'git push origin v{ver_str}')

    @staticmethod
    def test_all():
        # Build and test all
        SubProcessor.docker_down()
        click.clear()
        SubProcessor.docker_build()
        subprocess.run('docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml '
                       'run -e TEST_PARALLEL=True host bash host/test_all.sh')

    @staticmethod
    def test_loop(num_loops=10):
        # Build and test all
        SubProcessor.docker_down()
        click.clear()
        SubProcessor.docker_build()
        subprocess.run(f'docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml '
                       f'run -e TEST_PARALLEL=True host bash host/test_loop.sh {num_loops}')

    @staticmethod
    def env_local():
        subprocess.run('python secret_builder.py local')

    @staticmethod
    def env_docker():
        subprocess.run('python secret_builder.py docker')


@click.command()
@click.option('--mode', help='run the different versions of the server on the local machine', default='l',
              prompt='''
Which server should be run?

d - docker down
l - flask debug on localhost (lb to rebuild)
m - flask debug for mobile (mb to rebuild)
i - integration testing server (ib to rebuild)
s - storybook server (sb to rebuild)
k - sveltekit server (kb to rebuild)
n - run notebook server
c - clean and rebuild all
x - build and run all tests
''')
def run_server(mode):
    sp = SubProcessor()
    if mode == 'd':
        # Docker Down
        sp.docker_down()
    elif mode == 'l':
        # Flask debug localhost
        sp.env_local()
        sp.docker_down()
        sp.debug_up()
    elif mode == 'lb':
        # Flask debug localhost
        sp.env_local()
        sp.docker_build()
        sp.debug_up()
    elif mode == 'm':
        # Flask debug mobile
        sp.env_local()
        sp.debug_mobile_up()
    elif mode == 'mb':
        # Flask debug mobile
        sp.env_local()
        sp.docker_build()
        sp.debug_mobile_up()
    elif mode == 'i':
        # Integration Server
        sp.docker_down()
        sp.docker_up_integration()
    elif mode == 'ib':
        # Integration Server
        sp.docker_down()
        sp.docker_build(force_rm=True)
        sp.docker_up_integration()
    elif mode == 's':
        # Storybook server
        sp.storybook_up()
    elif mode == 'sb':
        # Storybook server
        sp.storybook_up(do_build=True)
    elif mode == 'k':
        # Sveltekit server
        sp.debug_svelte()
    elif mode == 'kb':
        # Sveltekit server
        sp.debug_svelte(do_build=True)
    elif mode == 'n':
        # Notebook Server
        subprocess.run(f'docker build -f eda/Dockerfile --rm -t notebooks .')
        subprocess.run(f'docker run -h notebook -it -e GRANT_SUDO=yes --user root -p 8888:8888 --rm '
                       f'--mount type=bind,source={os.getcwd()}/data,target=/home/jovyan/data '
                       f'--mount type=bind,source={os.getcwd()}/eda/notebooks,target=/home/jovyan/notebooks '
                       f'--mount type=bind,source={os.getcwd()}/eda/models,target=/home/jovyan/models '
                       f'--mount type=bind,source={os.getcwd()}/local.env,target=/home/jovyan/local.env '
                       f'notebooks')
    elif mode == 'c':
        # Clean and rebuild all
        sp.docker_down()
        subprocess.run('docker system prune -a --force')
        sp.docker_build(force_rm=True)
        sp.upgrade_db()
    elif mode == 'x':
        # Build and test all
        sp.test_all()


@click.command()
@click.option('--msg', help='please enter the commit message for this new migration', default='',
              prompt='''
Please enter the commit message for this new migration

''')
def new_migration(msg):
    sp = SubProcessor()
    sp.docker_down()
    subprocess.run(f'docker build -f Dockerfile --target api --rm -t api:latest .')
    sp.upgrade_db()
    print('\n\nmigration 1')
    subprocess.run(f'docker-compose run api flask db migrate -m "{msg}"')


@click.command()
@click.option('--mode', help='run the different versions of the server on the local machine', default='l',
              prompt='''
Which server should be run?

u - upgrade db (flask db upgrade)
n - new migration (flask db migrate -m ???)
d - downgrade db (flask db downgrade)
''')
def run_migrations(mode):
    sp = SubProcessor()
    if mode == 'u':
        # Upgrade DB
        # sp.docker_down()
        subprocess.run(f'docker run api flask db upgrade')
    elif mode == 'n':
        # New migration
        # sp.docker_down()
        new_migration()
    elif mode == 'd':
        # Downgrade DB
        # sp.docker_down()
        subprocess.run(f'docker run api flask db downgrade')


@click.command()
@click.option('--mode', help='run tests against the docker-compose apps and/or staging server', default='0',
              prompt='''
Which tests should be run?

0 - all (default)
1 - unit tests
2 - integration tests
3 - local acceptance tests
4 - remote acceptance tests
5 - safety
6 - locust vs staging
7 - stress testing (test_all x 10)
''')
def run_tests(mode):
    """
    Run all of the tests
    """
    sp = SubProcessor()
    # Set up env for docker tests
    sp.env_docker()
    if mode == '0':
        # Build and test all
        sp.test_all()
    elif mode == '1':
        # Unit Tests
        sp.docker_down()
        sp.docker_build()
        subprocess.run('docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml '
                       'run host python -m unittest discover -s tests.unit_tests -vvv ')
    elif mode == '2':
        # Integration Tests
        sp.docker_down()
        sp.docker_build()
        subprocess.run('docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml '
                       'run -e TEST_PARALLEL=True host unittest-parallel -s tests.integration_tests -vvv ')
    elif mode == '3':
        # Local Acceptance Tests
        sp.docker_down()
        sp.docker_build()
        subprocess.run('docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml '
                       'run -e TEST_PARALLEL=True host unittest-parallel -s tests.acceptance_tests -vvv ')
    elif mode == '4':
        # Remote Acceptance Tests
        sp.docker_down()
        sp.upgrade_db()
        ver = Version()
        sp.wait_for_version_number(target_url=staging_server_url, target_version=ver.version)
        subprocess.run(f'docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml run '
                       f'-e SERVER_URL={staging_server_url} '
                       f'host python -m unittest tests.acceptance_tests')
    elif mode == '5':
        # Safety - requirements vulnerability analysis
        subprocess.run(f'pip install safety --user')
        subprocess.run(f'python -m safety check -r api/requirements.txt --full-report')
        subprocess.run(f'python -m safety check -r notebooks/requirements.txt --full-report')
    elif mode == '6':
        # Locust - load testing vs staging with a web ui
        sp.docker_down()
        subprocess.run('docker-compose -f docker-compose.locust.yaml up --scale worker=4')
    elif mode == '7':
        # Stress testing - repeat the tests in order to make them more resilient
        sp.test_loop()
    elif mode == '8':
        # Test all without building
        subprocess.run('docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml '
                       'run -e TEST_PARALLEL=True host bash host/test_all.sh')


@click.command()
@click.option('--mode', help='use git to tag and push the code revision',
              prompt='''
What would you like to do with git?

0 - commit, bump patch, and push all
1 - commit, bump minor, and push all
2 - bump patch and push all
3 - bump minor and push all
4 - bump patch
5 - bump minor
6 - commit
''')
@click.option('--message', help='this message will be added to the git tag and the history.rst file',
              prompt='''What message would you like to add to the tag?''')
def run_git(mode, message):
    ver = Version()
    sp = SubProcessor()
    if mode == '0':
        # commit, bump patch, and push all
        sp.git_bump(how='patch', message=message, do_commit=True, do_push=True)
    elif mode == '1':
        # commit, bump minor, and push all
        sp.git_bump(how='minor', message=message, do_commit=True, do_push=True)
    elif mode == '2':
        # bump patch and push all
        sp.git_bump(how='patch', message=message, do_commit=False, do_push=True)
    elif mode == '3':
        # bump minor and push all
        sp.git_bump(how='minor', message=message, do_commit=False, do_push=True)
    elif mode == '4':
        # bump patch
        sp.git_bump(how='patch', message=message, do_commit=False, do_push=False)
    elif mode == '5':
        # bump minor
        sp.git_bump(how='minor', message=message, do_commit=False, do_push=False)
    elif mode == '6':
        # commit
        sp.git_commit(message=message)


@click.command()
@click.option('--message', help='this message will be added to the git tag and the history.rst file',
              prompt='''What message would you like to add to the tag?''')
def run_git_bump_patch_push(message):
    sp = SubProcessor()
    sp.git_bump(how='patch', message=message, do_commit=True, do_push=True)


@click.command()
@click.option('--mode', help='run the different versions of the server on the local machine', default='0',
              prompt='''
What would you like to do with docs?

0 - compile and build docs
1 - compile docs
2 - build docs
3 - view docs
''')
def run_docs(mode):
    wd = os.getcwd()
    if mode == '0':
        # compile and build docs
        docs_folder = os.path.join(Config.PROJECT_DIR, 'docs')
        subprocess.run(f'sphinx-apidoc -o {docs_folder}/source .')
        subprocess.run(f'docs_make.bat html')
    elif mode == '1':
        # compile docs
        subprocess.run('sphinx-apidoc -o docs/source ../..')
    elif mode == '2':
        # build docs
        subprocess.run('docs/make.bat html')
    elif mode == '3':
        # view docs
        subprocess.run('docs/make.bat html')
        os.chdir(wd)
        from selenium import webdriver
        driver = webdriver.Chrome()
        driver.get(os.path.abspath('./docs/build/html/index.html'))
    os.chdir(wd)


@click.command()
@click.option('--mode', help='compile different versions of the env vars for the app', default='0',
              prompt='''
What environment are you compiling for?

0 - docker-compose
1 - local debugging
''')
def run_envs(mode):
    sp = SubProcessor()
    if mode == '0':
        sp.env_docker()
    elif mode == '1':
        sp.env_local()


@click.command()
@click.option('--program', help='The program to run.', default='0',
              prompt='''
Which program would you like to run?
( Values marked with * are default args )

s - server menu
x - test menu
d - docs menu
g - git menu
m - migrations menu
e - compile env files

Shortcuts:
0 - run integration server
1 - render new orders
2 - render prompts pages
b - bump patch, commit, and push all
c - clear shell
''')
def main(program):
    sp = SubProcessor()
    if program == 's':
        run_server()
    elif program == 'x':
        run_tests()
    elif program == 'g':
        run_git()
    elif program == 'd':
        run_docs()
    elif program == 'm':
        run_migrations()
    elif program == 'e':
        run_envs()
    elif program == 'b':
        run_git_bump_patch_push()
    elif program == '0':
        # Integration Server
        sp.debug_up()
    elif program == '1':
        sp.docker_down()
        sp.upgrade_db()
        subprocess.run('docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml '
                       'run -e DEBUG=False -e DOWNLOADER_UID=compressor -e DOWNLOADER_UID=compressor '
                       '-e ORDERS_DIR=\\\\NAS\\home\\Drive\\Organizer\\LuminaryHandbook\\Operations\\Orders '
                       '-p 5005:5005 host python -m tests.fuzzer json')
    elif program == '2':
        sp.docker_down()
        sp.upgrade_db()
        subprocess.run('docker-compose run -e FLASK_DEBUG=1 -p 5005:5005 api '
                       'python -m tests_integration.fuzzer prompts')
    elif program == 'c':
        click.clear()


if __name__ == '__main__':
    main()
