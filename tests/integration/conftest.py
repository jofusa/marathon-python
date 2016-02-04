import os
import time
import pytest

from compose.cli import command

import marathon

from utils import retry


def get_compose_service(service_name):
    """Returns a compose object for the service"""
    cmd = command.Command()
    project = cmd.get_project(cmd.get_config_path('./tests/docker-compose.yml'))
    return project.get_service(service_name)


def get_marathon_connection_string():
    return 'http://localhost:8080'


@pytest.fixture(scope='function')
def client():
    client = marathon.MarathonClient(get_marathon_connection_string())

    def ensure_connection():
        assert client.get_info()
    retry(ensure_connection, exception_to_retry=(AssertionError, marathon.MarathonError))

    for app in client.list_apps():
        client.delete_app(app.id, force=True)

    def ensure_marathon_empty():
        assert not client.list_apps()
    retry(ensure_marathon_empty)

    return client
