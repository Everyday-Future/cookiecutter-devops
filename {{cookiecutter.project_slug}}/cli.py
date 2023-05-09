import os
import time
import dotenv
import click
import subprocess
import requests
from config import Version, Config

dotenv.load_dotenv('.env')
local_server_url = Config.SERVER_URL
staging_server_url = Config.CLIENT_SERVER_URL


class SubProcessor:
    """
    Run shell subprocesses with python
    """

    @staticmethod
    def docker_down():
        subprocess.call('docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml '
                        'down --remove-orphans', shell=True)

    @staticmethod
    def upgrade_db():
        subprocess.call('docker-compose run -e FLASK_DEBUG=1 -p 5008:5008 api flask db upgrade', shell=True)

    @staticmethod
    def docker_up():
        subprocess.call('docker-compose up', shell=True)

    @staticmethod
    def docker_up_integration():
        subprocess.call('docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml up', shell=True)

    @classmethod
    def docker_build(cls, force_rm=False):
        cls.docker_down()
        force_rm_str = ""
        if force_rm is True:
            force_rm_str = '--force-rm'
        subprocess.call(f'docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml '
                        f'build --parallel {force_rm_str}', shell=True)

    @classmethod
    def debug_up(cls):
        cls.docker_down()
        cls.upgrade_db()
        subprocess.call('docker-compose -f docker-compose.yaml '
                        'run -e FLASK_DEBUG=1 -e SERVER_NAME=localhost:5001 -e CLIENT_HOST=localhost '
                        '-e CLIENT_PORT=5005 -e USE_HTTPS=False -p 5001:5001 '
                        'api flask run --host=0.0.0.0 --port=5001', shell=True)

    @classmethod
    def debug_svelte(cls, do_build=False):
        cls.docker_down()
        cls.upgrade_db()
        if do_build is True:
            subprocess.call(f'docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml '
                            f'build --force-rm --parallel ', shell=True)
        subprocess.call('docker-compose -f docker-compose.yaml -f docker-compose.dev.yaml up', shell=True)

    @staticmethod
    def test_all():
        # Build and test all
        SubProcessor.docker_down()
        click.clear()
        SubProcessor.docker_build(force_rm=True)
        subprocess.call('docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml '
                        'run -e TEST_PARALLEL=True host bash host/test_all.sh', shell=True)

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
    def git_commit(message):
        """
        bump the version number and tag in git with it
        :param message: The message to add to the commit
        """
        subprocess.call(f'git add .', shell=True)
        subprocess.call(f'git commit -m "{message}"', shell=True)

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
        subprocess.call(f'git tag -a v{ver_str} -m "{message}"', shell=True)
        # push if specified
        if do_push is True:
            subprocess.call(f'git push origin v{ver_str}', shell=True)

    @staticmethod
    def env_local():
        subprocess.call('python -m host.secret_builder local', shell=True)

    @staticmethod
    def env_docker():
        subprocess.call('python -m host.secret_builder docker', shell=True)

    @staticmethod
    def env_acceptance():
        subprocess.call('python -m host.secret_builder acceptance', shell=True)


@click.command()
@click.option('--mode', help='run the different versions of the server on the local machine', default='l',
              prompt='''
Which server should be run?

d - docker down
l - flask debug on localhost (lb to rebuild)
i - integration testing server (ib to rebuild)
f - frontend server (kb to rebuild)
b - rebuild all
n - run notebook server
r - run redirect server
c - clean all
C - clean and rebuild all
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
    elif mode == 'i':
        # Integration Server
        sp.docker_down()
        sp.env_docker()
        sp.docker_up_integration()
    elif mode == 'ib':
        # Integration Server
        sp.docker_down()
        sp.docker_build(force_rm=True)
        sp.docker_up_integration()
    elif mode == 'f':
        # Sveltekit server
        sp.debug_svelte()
    elif mode == 'fb':
        # Sveltekit server
        sp.debug_svelte(do_build=True)
    elif mode == 'b':
        # rebuild all
        sp.docker_down()
        sp.docker_build(force_rm=True)
    elif mode == 'n':
        # Notebook Server
        subprocess.call(f'docker build -f Dockerfile-notebook --rm -t notebooks .', shell=True)
        subprocess.call(f'docker run -h notebook -it -e GRANT_SUDO=yes --user root -p 8888:8888 --rm '
                        f'--mount type=bind,source={os.getcwd()}/data,target=/home/jovyan/data '
                        f'--mount type=bind,source={os.getcwd()}/notebooks,target=/home/jovyan/notebooks '
                        f'--mount type=bind,source={os.getcwd()}/data/models,target=/home/jovyan/models '
                        f'--mount type=bind,source={os.getcwd()}/integration.env,target=/home/jovyan/integration.env '
                        f'notebooks', shell=True)
    elif mode == 'r':
        # Redirect Server
        subprocess.call(f'docker build -f Dockerfile-redirect -t redirect .', shell=True)
        subprocess.call(f'docker run -h redirect -it -p 5050:5000 --rm redirect', shell=True)
    elif mode == 'c':
        # Clean all
        sp.docker_down()
        subprocess.call('docker system prune -a --force', shell=True)
    elif mode == 'C':
        # Clean and rebuild all
        sp.docker_down()
        subprocess.call('docker system prune -a --force', shell=True)
        sp.docker_build(force_rm=True)
        sp.upgrade_db()


@click.command()
@click.option('--msg', help='please enter the commit message for this new migration', default='',
              prompt='''
Please enter the commit message for this new migration

''')
def new_migration(msg):
    sp = SubProcessor()
    sp.docker_down()
    subprocess.call(f'docker build -f Dockerfile --target api --rm -t api:latest .', shell=True)
    sp.upgrade_db()
    print('\n\nmigration 1')
    subprocess.call(f'docker-compose run api flask db migrate -m "{msg}"', shell=True)


@click.command()
@click.option('--mode', help='run the different versions of the server on the local machine', default='n',
              prompt='''
Which server should be run?

u - upgrade db (flask db upgrade)
n - new migration (flask db migrate -m ???)
d - downgrade db (flask db downgrade)
''')
def run_migrations(mode):
    if mode == 'u':
        # Upgrade DB
        # sp.docker_down()
        subprocess.call(f'docker run api flask db upgrade', shell=True)
    elif mode == 'n':
        # New migration
        # sp.docker_down()
        new_migration()
    elif mode == 'd':
        # Downgrade DB
        # sp.docker_down()
        subprocess.call(f'docker run api flask db downgrade', shell=True)


@click.command()
@click.option('--text_module', help='target the tests like integration_tests.test_adapter.StorageCase',
              default='unit_tests',
              prompt='Which specific tests would you like to run?')
def run_specific_tests(text_module):
    """
    Run all the tests
    """
    sp = SubProcessor()
    # Integration Tests
    sp.docker_down()
    subprocess.call('docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml '
                    f'run host python -m unittest tests.{text_module} -vvv ', shell=True)


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
8 - test all without building
x - run a specific test or group of tests
''')
def run_tests(mode):
    """
    Run all the tests
    """
    sp = SubProcessor()
    # Set up env for docker tests
    sp.env_docker()
    time.sleep(0.5)
    if mode == '0':
        # Build and test all
        sp.test_all()
    elif mode == '1':
        # Unit Tests
        sp.docker_down()
        subprocess.call('docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml '
                        'run host python -m unittest discover -s tests.unit_tests -vvv ', shell=True)
    elif mode == '2':
        # Integration Tests
        sp.docker_down()
        subprocess.call('docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml '
                        'run -e TEST_PARALLEL=True host unittest-parallel --jobs 4 -s tests.integration_tests -vvv ',
                        shell=True)
    elif mode == '3':
        # Local Acceptance Tests
        sp.docker_down()
        subprocess.call('docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml '
                        'run -e TEST_PARALLEL=True host unittest-parallel --jobs 4 -s tests.acceptance_tests -vvv ',
                        shell=True)
    elif mode == '4':
        # Remote Acceptance Tests
        sp.docker_down()
        sp.env_acceptance()
        sp.upgrade_db()
        subprocess.call(f'docker-compose -f docker-compose.acceptance.yaml run '
                        f'-e TEST_PARALLEL=True host unittest-parallel --jobs 4 -s tests.integration_tests -f -vvv',
                        shell=True)
    elif mode == '5':
        # Safety - requirements vulnerability analysis
        subprocess.call(f'pip install -r host/requirements.txt --user', shell=True)
        subprocess.call(f'python -m safety check -r api/requirements.txt --full-report', shell=True)
        subprocess.call(f'python -m safety check -r host/functions/etl-lake/requirements.txt --full-report', shell=True)
    elif mode == '6':
        # Locust - load testing vs staging with a web ui
        sp.docker_down()
        subprocess.call('docker-compose -f docker-compose.locust.yaml up --scale worker=4', shell=True)
    elif mode == '8':
        # Test all without building
        subprocess.call('docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml '
                        'run -e TEST_PARALLEL=True host bash host/test_all.sh', shell=True)
    elif mode == 'x':
        run_specific_tests()


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
''')
def run_docs(mode):
    wd = os.getcwd()
    if mode == '0':
        # compile and build docs
        docs_folder = os.path.join(Config.PROJECT_DIR, 'docs')
        subprocess.call(f'sphinx-apidoc -o {docs_folder}/source .', shell=True)
        subprocess.call(f'docs_make.bat html', shell=True)
    elif mode == '1':
        # compile docs
        subprocess.call('sphinx-apidoc -o docs/source ../..', shell=True)
    elif mode == '2':
        # build docs
        subprocess.call('docs_make.bat html', shell=True)
    os.chdir(wd)


@click.command()
@click.option('--mode', help='compile different versions of the env vars for the app', default='0',
              prompt='''
What environment are you compiling for?

0 - docker-compose
1 - local debugging
2 - develop (remote debugging)
''')
def run_envs(mode):
    sp = SubProcessor()
    if mode == '0':
        sp.env_docker()
    elif mode == '1':
        sp.env_local()
    elif mode == '2':
        sp.env_acceptance()


def run_build_compiler():
    """
    Compile the build pipeline and cloud functions
    :return:
    :rtype:
    """
    subprocess.run(f'python -B host/build_compiler.py')


@click.option('--filename', help='make a shell script edited in windows executable in docker',
              prompt='''What file should be converted?''')
def run_dos2unix(filename):
    subprocess.run(f'dos2unix {filename}')
    subprocess.run(f'git update-index --chmod=+x {filename}')


@click.command()
@click.option('--program', help='The program to run.', default='0',
              prompt='''
Which program would you like to run?
( Values marked with * are default args )

s - server menu
x - test menu
t - toolkit menu
d - docs menu
g - git menu
m - migrations menu
e - compile env files
q - query against Data Lakehouse
p - compile build pipeline
l - stream docker-compose logs

Shortcuts:
0 - run integration server
b - bump patch, commit, and push all
c - clear shell
u - run dos2unix on file
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
    elif program == 'p':
        run_build_compiler()
    elif program == 'b':
        run_git_bump_patch_push()
    elif program == 'l':
        subprocess.call('docker-compose -f docker-compose.yaml -f docker-compose.integration.yaml logs -f -t',
                        shell=True)
    elif program == '0':
        # Local Server
        click.clear()
        sp.env_local()
        sp.docker_down()
        sp.debug_up()
    elif program == 'c':
        click.clear()
    elif program == 'u':
        run_dos2unix()


if __name__ == '__main__':
    main()
