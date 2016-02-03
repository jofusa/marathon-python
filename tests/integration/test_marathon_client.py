import time
import pytest

import uuid
import marathon

from utils import retry

@pytest.fixture(scope='function')
def client(marathon_container):
    client = marathon.MarathonClient('http://localhost:8082')

    def ensure_connection():
        assert client.get_info()
    retry(ensure_connection, exception_to_retry=(AssertionError, marathon.MarathonError))
    return client


def test_marathon_create_client_smoke_test(client):
    """
    Simple smoke test to ensure docker containers are started
    """
    assert client.get_info()


def test_create_and_destory_trivial_app(client):
    app_id = str(uuid.uuid4())
    client.create_app(app_id, marathon.MarathonApp(cmd='sleep 3600', mem=16, cpus=1, instances=5))
    app = client.get_app(app_id)
    assert app.id == '/' + app_id
    time.sleep(4)

    # def test_kill():
        # app = client.get_app(app_id)
        # assert app.tasks
        # client.kill_task(app_id=app_id, task_id=app.tasks[0].id, scale=True)
    # retry(test_kill)


def test_deploy_complex_app(client):
    complex_app_name = 'test-complex-app'
    app_config = {
        'container': {
            'type': 'DOCKER',
            'docker': {
                'portMappings': [{'protocol': 'tcp', 'containerPort': 8888, 'hostPort': 0}],
                'image': u'localhost/fake_docker_url',
                'network': 'BRIDGE',
            },
            'volumes': [{'hostPath': u'/etc/stuff', 'containerPath': u'/etc/stuff', 'mode': 'RO'}],
        },
        'instances': 1,
        'mem': 30,
        'args': [],
        'backoff_factor': 2,
        'cpus': 0.25,
        'uris': ['file:///root/.dockercfg'],
        'backoff_seconds': 1,
        'constraints': None,
        'cmd': u'/bin/true',
        'health_checks': [
            {
                'protocol': 'HTTP',
                'path': '/health',
                'gracePeriodSeconds': 3,
                'intervalSeconds': 10,
                'portIndex': 0,
                'timeoutSeconds': 10,
                'maxConsecutiveFailures': 3
            },
        ],
    }
    client.create_app(complex_app_name, marathon.MarathonApp(**app_config))

    assert client.get_app(complex_app_name)

    def wait_until_deployed():
        app = client.get_app(complex_app_name, embed_tasks=True)
        assert app.deployments
    retry(wait_until_deployed)

