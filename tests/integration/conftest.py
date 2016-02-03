import os
import time

import pytest

import docker
from docker.utils import kwargs_from_env, create_host_config


class DockerLog:
    def __init__(self, container, client):
        self.container = container
        self.client = client

    def __contains__(self, t):
        return t in self.logs

    @property
    def logs(self):
        return self.client.logs(self.container).decode()

    def __str__(self):
        return self.logs

    def __repr__(self):
        return self.logs


class AbstractDockerContainer(object):
    repository = None
    image_name = None
    tag = 'latest'
    port_mappings = None
    network_mode = 'bridge'
    env = {}

    _log = None

    def __init__(self, docker_client, tag=None):
        self.docker_client = docker_client
        if tag:
            self.tag = tag

    @property
    def full_image_name(self):
        if self.repository:
            return '{}/{}:{}'.format(self.repository, self.image_name, self.tag)
        else:
            return '{}:{}'.format(self.image_name, self.tag)

    @property
    def environment(self):
        return self.env

    def pull_container(self):
        if not self.docker_client.images(self.full_image_name):
            self.docker_client.pull(self.full_image_name)

    def start(self):
        self.pull_container()
        self.build_container()

        result = self.docker_client.start(self._container)
        time.sleep(1)
        return result

    def restart(self):
        result = self.docker_client.restart(self._container)
        time.sleep(1)
        return result

    def kill(self):
        return self.docker_client.kill(self._container)

    def build_container(self):
        if self.port_mappings:
            self._container = self.docker_client.create_container(
                image=self.full_image_name,
                environment=self.environment,
                ports=list(self.port_mappings.keys()),
                host_config=create_host_config(
                    port_bindings=self.port_mappings,
                    network_mode=self.network_mode
                )
            )
        else:
            self._container = self.docker_client.create_container(
                image=self.full_image_name,
                environment=self.environment,
                host_config=create_host_config(
                    network_mode=self.network_mode
                )
            )

    @property
    def ip(self):
        return self.docker_client.inspect_container(self._container)['NetworkSettings']['IPAddress']

    @property
    def log(self):
        if not self._log:
            self._log = DockerLog(self._container, self.docker_client)
        return self._log


@pytest.fixture(scope='session')
def docker_client():
    client_kwargs = docker.utils.kwargs_from_env(assert_hostname=False)
    return docker.Client(client_kwargs)


class ZookeeperDockerContainer(AbstractDockerContainer):
    repository = 'wurstmeister'
    image_name = 'zookeeper'
    port_mappings = {2181: 2181}


class MesosMasterDockerContainer(AbstractDockerContainer):
    repository = 'mesosphere'
    image_name = 'mesos-master'
    network_mode = 'host'

    def build_container(self):
        self._container = self.docker_client.create_container(
            command='--zk=zk://127.0.0.1:2181/mesos',
            image=self.full_image_name,
            environment=self.environment,
            host_config=create_host_config(
                network_mode=self.network_mode
            )
        )


class MesosSlaveDockerContainer(AbstractDockerContainer):
    repository = 'mesosphere'
    image_name = 'mesos-slave'
    network_mode = 'host'

    def build_container(self):
        self._container = self.docker_client.create_container(
            command='--master=zk://127.0.0.1:2181/mesos --hostname=127.0.0.1',
            image=self.full_image_name,
            environment=self.environment,
            host_config=create_host_config(
                network_mode=self.network_mode
            )
        )

class MarathonDockerContainer(AbstractDockerContainer):
    repository = 'mesosphere'
    image_name = 'marathon'
    network_mode = 'host'
    env = {
        'MARATHON_MASTER': '127.0.0.1:5050',
        'MARATHON_HTTP_PORT': 8081
    }


@pytest.yield_fixture(scope='session')
def zookeeper_container(docker_client):
    container = ZookeeperDockerContainer(docker_client)
    container.start()
    time.sleep(2)
    print(container.log) 
    yield container
    container.kill()


@pytest.yield_fixture(scope='session')
def mesos_master_container(docker_client):
    MESOSVERSION = os.getenv('MESOSVERSION', '0.24.1-0.2.35.ubuntu1404')
    print("STATRING MASTER WITH: {}".format(MESOSVERSION))
    container = MesosMasterDockerContainer(docker_client, tag=MESOSVERSION)
    container.start()
    time.sleep(2)
    print(container.log) 
    yield container
    container.kill()


@pytest.yield_fixture(scope='session')
def mesos_slave_container(docker_client):
    MESOSVERSION = os.getenv('MESOSVERSION', '0.24.1-0.2.35.ubuntu1404')
    print("STATRING SLAVE WITH: {}".format(MESOSVERSION))
    container = MesosSlaveDockerContainer(docker_client, tag=MESOSVERSION)
    container.start()
    time.sleep(2)
    print(container.log) 
    yield container
    container.kill()


@pytest.yield_fixture(scope='session')
def marathon_container(docker_client, mesos_master_container, mesos_slave_container, zookeeper_container):
    MARATHONVERSION = os.getenv('MARATHONVERSION', 'v0.11.0')
    container = MarathonDockerContainer(docker_client, tag=MARATHONVERSION)
    container.start()
    time.sleep(4)
    print(container.log) 
    # def test_marathon_up():
        # resp = requests.get('http://localhost:8081')
        # assert resp.ok

    # try:
        # retry(test_marathon_up, retry_time=30, wait_between_tries=0.5, exception_to_retry=(requests.exceptions.ConnectionError, AssertionError))
    # except AssertionError:
        # container.kill()
        # raise

    yield container
    container.kill()


# @pytest.yield_fixture(scope='session')
# def marathon_docker(docker_client, mesos_master_docker, zookeeper_docker):
    # container = MarathonDockerContainer(docker_client)
    # container.start()
    # time.sleep(2)
    # def test_marathon_up():
        # resp = requests.get('http://localhost:8081')
        # assert resp.ok

    # try:
        # retry(test_marathon_up, retry_time=30, wait_between_tries=0.5, exception_to_retry=(requests.exceptions.ConnectionError, AssertionError))
    # except AssertionError:
        # container.kill()
        # raise

    # yield container
    # container.kill()

