from flexmock import flexmock
from mfcloud.api import MfCloudApi, DnsService, SkyDnsServiceLocator, FtpEndpoint, GitEndpoint, LocalSkyDnsServiceLocator, LocalDeploymentEndpoint, IBalancer
from mfcloud.container import DockerLocal
from mfcloud.util import abstract
import pytest


def test_api():

    cloud = MfCloudApi()

    cloud.add_docker(DockerLocal())

    assert 1 == len(cloud.dockers())

    cloud.add_balancer(flexmock(abstract(IBalancer)))

    assert 1 == len(cloud.balancers())

    cloud.add_dns_service(DnsService(domains=['dev.modera.org']))

    assert 1 == len(cloud.dnses())

    cloud.add_service_locator(SkyDnsServiceLocator(host='foo'))

    assert 1 == len(cloud.locators())

    cloud.add_deployment_endpoint(FtpEndpoint())
    cloud.add_deployment_endpoint(GitEndpoint())

    assert 2 == len(cloud.endpoints())


def test_build_local_deployment():

    cloud = MfCloudApi()
    cloud.add_docker(DockerLocal())

    locator = LocalSkyDnsServiceLocator(host='foo')
    locator.ensure_started()

    cloud.add_service_locator(locator)

    cloud.add_deployment_endpoint(LocalDeploymentEndpoint(path='/foo/bar/baz'))



def test_api_wrong_types_passed():

    class InvalidType(object):
        pass

    cloud = MfCloudApi()

    with pytest.raises(TypeError):
        cloud.add_balancer(InvalidType())

    with pytest.raises(TypeError):
        cloud.add_dns_service(InvalidType())

    with pytest.raises(TypeError):
        cloud.add_service_locator(InvalidType())

    with pytest.raises(TypeError):
        cloud.add_deployment_endpoint(InvalidType())


