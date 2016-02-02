import pytest

import uuid
import marathon

from utils import retry

@pytest.fixture(scope='function')
def client(marathon_container):
    client = marathon.MarathonClient('http://localhost:8081')
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

    def test_kill():
        app = client.get_app(app_id)
        assert app.tasks
        client.kill_task(app_id=app_id, task_id=app.tasks[0].id, scale=True)
    retry(test_kill)


