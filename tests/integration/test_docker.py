

def test_docker_client(docker_client):
    assert docker_client.info()

def test_zookeeper_container(zookeeper_container):
    assert zookeeper_container.ip
