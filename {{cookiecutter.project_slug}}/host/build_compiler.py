import os


class BuildCompiler:
    """
    Create custom Cloud Build yaml files based on requested specs
    """

    def __init__(self):
        self.base_started = False
        self.builds_started = False
        self.deploys_started = False

    def reset(self):
        self.base_started = False
        self.builds_started = False
        self.deploys_started = False

    def get_base(self):
        self.base_started = True
        return """
#   # Start the build
#   # ------------------------------------
steps:
  - name: 'bash'
    id: 'build-start'
    args: ['echo', 'build started!']
        """

    @staticmethod
    def run_safety():
        return """
  # Run vulnerability analysis with safety
  # ------------------------------------
  - name: python
    id: 'install-safety'
    waitFor: [build-start]
    entrypoint: pip
    args: ["install", "safety", "Jinja2==3.0.1", "python-dotenv==0.21.0, "--user"]
  - name: python
    id: 'safety-check-api'
    waitFor: [install-safety]
    entrypoint: python
    args: ["-m", "safety", "check", "-i", "39642", "-i", "44715", "-i", "51668", "-r", "api/requirements.txt", "--full-report"]
  - name: python
    id: 'safety-check-etl'
    waitFor: [install-safety]
    entrypoint: python
    args: ["-m", "safety", "check", "-i", "39642", "-i", "44715", "-i", "51668", "-r", "host/functions/etl-lake/requirements.txt", "--full-report"]
  - name: 'bash'
    id: 'safety-passed'
    args: ['echo', 'python safety - no vulnerabilities found']
        """

    @staticmethod
    def get_secrets():
        """
        Get the secrets downloaded and compiled for a service
        :rtype:
        """
        return """
#   # Get secrets
#   # ------------------------------------
# Integration secrets template
  - name: gcr.io/cloud-builders/gcloud
    id: 'integration-secrets-template'
    waitFor: [build-start]
    entrypoint: 'bash'
    args: [ '-c', "gcloud secrets versions access latest --secret=secret-template --format='get(payload.data)' | tr '_-' '/+' | base64 -d > secret-template.env" ]
# Integration secrets template values
  - name: gcr.io/cloud-builders/gcloud
    id: 'integration-secrets-template-values'
    waitFor: [build-start]
    entrypoint: 'bash'
    args: [ '-c', "gcloud secrets versions access latest --secret=secret-template-values --format='get(payload.data)' | tr '_-' '/+' | base64 -d > secret-template-values.env" ]
# Copy explore instances and compile env vars into them
  - name: python
    id: 'compile-secrets-and-explore'
    entrypoint: python
    args: ["-m", "host.secret_builder", "${_STAGE}"]
  - name: 'bash'
    id: 'print-directory'
    args: ['ls']
        """

    @staticmethod
    def get_build():
        return """
  # Build Docker-Compose environment
  # ------------------------------------
  # Docker-compose selenium standalone chrome env for running integration tests here.
  - name: 'gcr.io/$PROJECT_ID/docker-compose'
    id: 'build-docker'
    args: [
        '-f', 'docker-compose.yaml',
        '-f', 'docker-compose.integration.yaml',
        '--env-file', 'integration.env',
        'build', '--parallel'
    ]
    env:
      - 'PROJECT_ID=$PROJECT_ID'
        """

    @staticmethod
    def get_unit_tests():
        return """
  # Run unit tests
  # ------------------------------------
  # unit-test-api
  - name: 'gcr.io/$PROJECT_ID/docker-compose'
    id: 'unit-test-api'
    args: [
        '-f', 'docker-compose.yaml',
        '-f', 'docker-compose.integration.yaml',
      'run', '--rm',
      'host',
      'python', '-m', 'unittest', 'discover', '-s', 'tests.unit_tests', '-vvv'
    ]
    env:
      - 'PROJECT_ID=$PROJECT_ID'
  # unit-tests-passed
  - name: 'bash'
    id: 'unit-tests-passed'
    waitFor: [unit-test-api]
    args: ['echo', 'unit_tests - all tests passing!']

  # Take containers down after unit_tests
  # ------------------------------------
  - name: 'gcr.io/$PROJECT_ID/docker-compose'
    id: 'docker-down'
    waitFor: [unit-test-api]
    args: [
        '-f', 'docker-compose.yaml',
        '-f', 'docker-compose.integration.yaml',
        'down',
    ]
    env:
      - 'PROJECT_ID=$PROJECT_ID'
        """

    @staticmethod
    def get_integration_acceptance_tests(test_mode='integration'):
        if test_mode == 'acceptance':
            server_url = """
        '-e', 'SERVER_URL=${_SERVER_STAGING_URL}',"""
        else:
            server_url = ''
        return f"""
  # Build and run {test_mode} tests
  # ------------------------------------
  # Docker-compose selenium standalone chrome env for running {test_mode} tests here.
  - name: 'gcr.io/$PROJECT_ID/docker-compose'
    id: '{test_mode}-tests'
    args: [
        '-f', 'docker-compose.yaml',
        '-f', 'docker-compose.integration.yaml',
        'run', {server_url}
        '-e', 'TEST_PARALLEL=True',
        'host',
        'unittest-parallel', '-s', 'tests/{test_mode}_tests', '-t', '.', '-vvv'
    ]
    env:
      - 'PROJECT_ID=$PROJECT_ID'
  - name: 'bash'
    id: '{test_mode}-tests-passed'
    args: ['echo', '{test_mode}_tests - all tests passing!']
        """

    def get_start_builds(self):
        self.builds_started = True
        return """
#   # Start docker image builds
#   # ------------------------------------
  - name: 'bash'
    id: 'start-builds'
    args: ['echo', 'start building images...']
        """

    @staticmethod
    def get_build_tag_push(target):
        """
        Build, tag, and push the Docker image
        :param target: The service to target for the build (api, explore, create)
        :type target: str
        :return:
        :rtype:
        """
        # Other services (create, explore-api, ...)
        dockerfile = f'Dockerfile-{target}'
        return f"""
  # Docker Build {target}:${{_STAGE}}
  - name: 'gcr.io/cloud-builders/docker'
    waitFor: [start-builds]
    id: 'build-{target}'
    args: ['build',
    '-f', '{dockerfile}',
    '-t', 'gcr.io/$PROJECT_ID/{target}:${{_STAGE}}',
    '-t', 'gcr.io/$PROJECT_ID/{target}:latest',
    '-t', '{target}',
    '--target', '{target}', '.']

  # Docker Push {target}:${{_STAGE}} image tagged latest (parallel)
  - name: 'gcr.io/cloud-builders/docker'
    waitFor: [build-{target}]
    args: ['push', 'gcr.io/$PROJECT_ID/{target}:latest']

  # Docker Push {target}:${{_STAGE}} image tagged $instance (parallel)
  - name: 'gcr.io/cloud-builders/docker'
    waitFor: [build-{target}]
    args: ['push', 'gcr.io/$PROJECT_ID/{target}:${{_STAGE}}']
        """

    def get_start_deploys(self):
        self.deploys_started = True
        return """
#   # Start Cloud Run / Function deployments
#   # ------------------------------------
  - name: 'bash'
    id: 'start-deploys'
    args: ['echo', 'starting cloud run deployments...']
        """

    def get_deploy_cloud_run(self, target):
        if self.builds_started is False or self.deploys_started is False:
            raise ValueError('get_start_builds and get_start_deploys must be run before deployments')
        return f"""
  # Deploy Cloud Run - {target}
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    waitFor: [start-deploys]
    entrypoint: gcloud
    args:
    - 'run'
    - 'deploy'
    - '{target}-${{_STAGE}}'
    - '--image'
    - 'gcr.io/$PROJECT_ID/{target}:${{_STAGE}}'
    - '--region'
    - 'us-central1'
    - '--platform'
    - 'managed'
    - '--allow-unauthenticated'
        """

    @staticmethod
    def get_deploy_cloud_function(function_name, source, entrypoint):
        return f"""
  # Deploy to Cloud Function - {function_name}
  - name: gcr.io/cloud-builders/gcloud
    id: '{function_name}-${{_STAGE}}-function-deploy'
    entrypoint: gcloud
    args:
    - 'functions'
    - 'deploy'
    - '{function_name}-${{_STAGE}}'
    - '--gen2'
    - '--region=us-central1'
    - '--source={source}'
    - '--trigger-http'
    - '--runtime=python39'
    - '--entry-point={entrypoint}'
    - '--allow-unauthenticated'
        """

    @staticmethod
    def get_build_options():
        return """
options:
  machineType: 'N1_HIGHCPU_8'
        """

    @staticmethod
    def get_timeout(timeout_seconds="3600"):
        return f"""
timeout: {timeout_seconds}s
        """


def get_api_build(build_mode='all', timeout_seconds="3600"):
    """
    Build the API for the Explore tool
    :param build_mode: What mode to build for from (test, deploy, all)
    :type build_mode: str
    :param timeout_seconds:
    :type timeout_seconds:
    :return:
    :rtype:
    """
    bc = BuildCompiler()
    build_file = bc.get_base() + bc.run_safety() + bc.get_secrets()
    if build_mode in ('test', 'all'):
        build_file += bc.get_build() + bc.get_unit_tests() + bc.get_integration_acceptance_tests()
    if build_mode in ('deploy', 'all'):
        build_file += bc.get_start_builds() + bc.get_build_tag_push(target='api')
        build_file += bc.get_start_deploys() + bc.get_deploy_cloud_run(target='api')
        build_file += bc.get_integration_acceptance_tests(test_mode='acceptance')
    if build_mode in ('test', 'all'):
        build_file += bc.get_build_options()
    build_file += bc.get_timeout(timeout_seconds=timeout_seconds)
    return build_file


def get_frontend_build(build_mode='all', timeout_seconds="3600"):
    """
    Build the svelte frontend
    :param build_mode: What mode to build for from (test, deploy, all)
    :type build_mode: str
    :param timeout_seconds:
    :type timeout_seconds:
    :return:
    :rtype:
    """
    bc = BuildCompiler()
    build_file = bc.get_base() + bc.run_safety() + bc.get_secrets()
    if build_mode in ('test', 'all'):
        build_file += bc.get_build() + bc.get_unit_tests() + bc.get_integration_acceptance_tests()
    if build_mode in ('deploy', 'all'):
        build_file += bc.get_start_builds() + bc.get_build_tag_push(target='frontend')
        build_file += bc.get_start_deploys() + bc.get_deploy_cloud_run(target='frontend')
    build_file += bc.get_timeout(timeout_seconds=timeout_seconds)
    return build_file


def get_redirect_build(build_mode='all', timeout_seconds="3600"):
    """
    Build the frontend redirect server
    :param build_mode: What mode to build for from (test, deploy, all)
    :type build_mode: str
    :param timeout_seconds:
    :type timeout_seconds:
    :return:
    :rtype:
    """
    bc = BuildCompiler()
    build_file = bc.get_base() + bc.run_safety() + bc.get_secrets()
    if build_mode in ('deploy', 'all'):
        build_file += bc.get_start_builds() + bc.get_build_tag_push(target='redirect')
        build_file += bc.get_start_deploys() + bc.get_deploy_cloud_run(target='redirect')
    build_file += bc.get_timeout(timeout_seconds=timeout_seconds)
    return build_file


def get_functions_build(timeout_seconds="3600"):
    """
    Build and deploy Cloud Functions
    :param timeout_seconds:
    :type timeout_seconds:
    :return:
    :rtype:
    """
    bc = BuildCompiler()
    build_file = bc.get_base()
    build_file += bc.get_deploy_cloud_function(function_name='etl-lake',
                                               source='./host/functions/etl-lake',
                                               entrypoint='run')
    build_file += bc.get_timeout(timeout_seconds=timeout_seconds)
    return build_file


def save_build(fname, build_str):
    with open(os.path.join('host/cloudbuild', fname), 'w') as fp:
        fp.write(build_str)


def build_all():
    for build_mode in ('test', 'deploy'):
        # --- api ---
        build_str = get_api_build(build_mode=build_mode)
        save_build(f'cloudbuild-api-{build_mode}.yaml', build_str)
    build_mode = 'deploy'
    # --- frontend ---
    build_str = get_frontend_build(build_mode=build_mode)
    save_build(f'cloudbuild-frontend-{build_mode}.yaml', build_str)
    # --- frontend hotfix ---
    build_str = get_frontend_build(build_mode=build_mode)
    save_build(f'cloudbuild-frontend-{build_mode}-hotfix.yaml', build_str)
    # --- frontend redirect ---
    build_str = get_redirect_build(build_mode=build_mode)
    save_build(f'cloudbuild-redirect-{build_mode}.yaml', build_str)
    # --- cloud functions ---
    build_str = get_functions_build()
    save_build(f'cloudbuild-functions-{build_mode}.yaml', build_str)
    # --- preview deploy ---
    bc = BuildCompiler()
    build_str = bc.get_base() + bc.run_safety() + bc.get_secrets()
    build_str += bc.get_start_builds() + bc.get_build_tag_push(target='api')
    build_str += bc.get_build_tag_push(target='frontend')
    build_str += bc.get_start_deploys() + bc.get_deploy_cloud_run(target='api')
    build_str += bc.get_deploy_cloud_run(target='frontend')
    # TODO - Add acceptance tests
    build_str += bc.get_timeout()
    save_build(f'cloudbuild-stack-preview.yaml', build_str)


if __name__ == '__main__':
    build_all()
    print('\n\nBuild pipeline complete!\n\n')
