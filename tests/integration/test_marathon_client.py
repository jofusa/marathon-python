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


@pytest.fixture(scope='function')
def trivial_app(client):
    app_id = str(uuid.uuid4())
    client.create_app(app_id, marathon.MarathonApp(cmd='sleep 3600', mem=16, cpus=0.1, instances=5))

    def wait_until_deployed():
        app = client.get_app(app_id)
        assert app.tasks_running == 5
    retry(wait_until_deployed)

    app = client.get_app(app_id)
    return app


@pytest.fixture(scope='function')
def complex_app(client):
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
    app = client.get_app(complex_app_name, embed_tasks=True)
    return app


def test_marathon_create_client_smoke_test(client):
    """
    Scenario: Metadata can be fetched
      Given a working marathon instance
       Then we get the marathon instance's info
    """
    assert client.get_info()


def test_trivial_app(trivial_app, client):
    """
      Scenario: Trivial apps can be deployed
        Given a working marathon instance
         When we create a trivial new app
         Then we should see the trivial app running via the marathon api

      Scenario: App tasks can be listed
        Given a working marathon instance
         When we create a trivial new app
          And we wait the trivial app deployment finish
         Then we should be able to list tasks of the trivial app
    """
    app = client.get_app(trivial_app.id)
    tasks = client.list_tasks(trivial_app.id)
    assert len(tasks) == app.instances


def test_complex_app_deploy(complex_app, client):
    """
     Scenario: Complex apps can be deployed
        Given a working marathon instance
         When we create a complex new app
         Then we should see the complex app running via the marathon api
    """
    assert client.get_app(complex_app.id)


def test_kill_trivial_app(trivial_app, client):
    """
      Scenario: App tasks can be killed
        Given a working marathon instance
         When we create a trivial new app
          And we wait the trivial app deployment finish
         Then we should be able to kill the tasks
    """
    app_id = trivial_app.id
    client.kill_task(app_id=app_id, task_id=trivial_app.tasks[0].id, scale=True)

    def test_app_killed_and_scaled():
        assert client.get_app(app_id).tasks_running == 4
    retry(test_app_killed_and_scaled)


def test_kill_given_tasks(trivial_app, client): 
    """
      Scenario: A list of app tasks can be killed
        Given a working marathon instance
         When we create a trivial new app
          And we wait the trivial app deployment finish
         Then we should be able to kill the #0,1,2 tasks of the trivial app
    """
    task_to_kill = [trivial_app.tasks[index].id for index in [0,1,2]]
    client.kill_given_tasks(task_to_kill)
