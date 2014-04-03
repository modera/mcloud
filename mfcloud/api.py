from abc import ABCMeta, abstractmethod
from mfcloud.util import accepts


class Interface(object):
    __metaclass__ = ABCMeta


class IMfCloudCompontent(Interface):

    @abstractmethod
    def set_event_bus(self, bus):
        pass


class IDocker(Interface):
    pass


class IBalancer(Interface):

    @abstractmethod
    def get_domains(self):
        pass

    @abstractmethod
    def point_domain(self, domain, hostname, port):
        pass

    @abstractmethod
    def remove_domain(self, domain, hostname, port):
        pass


class IDnsService(Interface):

    @abstractmethod
    def get_domains(self):
        pass

    @abstractmethod
    def point_domain(self, domain, record_type, destination):
        pass

    @abstractmethod
    def remove_domain(self, domain, record_type, destination):
        pass


class IServiceLocator(Interface):

    @abstractmethod
    def register_application_service(self, application_name, application_version, service, ip):
        pass

    @abstractmethod
    def clear_application_services(self, application_name, application_version, service, ip):
        pass


class IDeploymentEndpoint(Interface):

    @abstractmethod
    def on_application_created(self, application_name):
        pass

    @abstractmethod
    def on_application_removed(self, application_name):
        pass

    @abstractmethod
    def on_application_version_removed(self, application_name):
        pass

    @abstractmethod
    def list_application_versions(self, application_name):
        pass

    @abstractmethod
    def get_application_path(self, application_name, application_version):
        pass


class MfCloudApi():
    """
    Main facade for MfCloud services
    """

    def __init__(self):
        self._dockers = []
        self._balancers = []
        self._dnses = []
        self._locators = []
        self._endpoints = []

    @accepts(IDocker)
    def add_docker(self, docker):
        self._dockers.append(docker)

    @accepts(IBalancer)
    def add_balancer(self, balancer):
        self._balancers.append(balancer)

    @accepts(IDnsService)
    def add_dns_service(self, dns_service):
        self._dnses.append(dns_service)

    @accepts(IServiceLocator)
    def add_service_locator(self, locator):
        self._locators.append(locator)

    @accepts(IDeploymentEndpoint)
    def add_deployment_endpoint(self, endpoint):
        self._endpoints.append(endpoint)

    def dockers(self):
        return self._dockers

    def balancers(self):
        return self._balancers

    def dnses(self):
        return self._dnses

    def locators(self):
        return self._locators

    def endpoints(self):
        return self._endpoints


class DockerLocal(IDocker):

    def __init__(self, **kwargs):
        super(DockerLocal, self).__init__()


class DnsService(IDnsService):

    def __init__(self, **kwargs):
        super(DnsService, self).__init__()

    def remove_domain(self, domain, record_type, destination):
        super(DnsService, self).remove_domain(domain, record_type, destination)

    def point_domain(self, domain, record_type, destination):
        super(DnsService, self).point_domain(domain, record_type, destination)

    def get_domains(self):
        super(DnsService, self).get_domains()


class SkyDnsServiceLocator(IServiceLocator):

    def __init__(self, **kwargs):
        super(SkyDnsServiceLocator, self).__init__()

    def clear_application_services(self, application_name, application_version, service, ip):
        super(SkyDnsServiceLocator, self).clear_application_services(application_name, application_version, service, ip)

    def register_application_service(self, application_name, application_version, service, ip):
        super(SkyDnsServiceLocator, self).register_application_service(application_name, application_version, service,
                                                                       ip)


class LocalSkyDnsServiceLocator(SkyDnsServiceLocator):

    def ensure_started(self):
        pass


class FtpEndpoint(IDeploymentEndpoint):

    def on_application_created(self, application_name):
        super(FtpEndpoint, self).on_application_created(application_name)

    def list_application_versions(self, application_name):
        super(FtpEndpoint, self).list_application_versions(application_name)

    def on_application_version_removed(self, application_name):
        super(FtpEndpoint, self).on_application_version_removed(application_name)

    def get_application_path(self, application_name, application_version):
        super(FtpEndpoint, self).get_application_path(application_name, application_version)

    def on_application_removed(self, application_name):
        super(FtpEndpoint, self).on_application_removed(application_name)

    def __init__(self, **kwargs):
        super(FtpEndpoint, self).__init__()


class GitEndpoint(IDeploymentEndpoint):

    def on_application_created(self, application_name):
        super(GitEndpoint, self).on_application_created(application_name)

    def list_application_versions(self, application_name):
        super(GitEndpoint, self).list_application_versions(application_name)

    def on_application_version_removed(self, application_name):
        super(GitEndpoint, self).on_application_version_removed(application_name)

    def get_application_path(self, application_name, application_version):
        super(GitEndpoint, self).get_application_path(application_name, application_version)

    def on_application_removed(self, application_name):
        super(GitEndpoint, self).on_application_removed(application_name)

    def __init__(self, **kwargs):
        super(GitEndpoint, self).__init__()


class LocalDeploymentEndpoint(IDeploymentEndpoint):

    def __init__(self, **kwargs):
        super(LocalDeploymentEndpoint, self).__init__()

    def on_application_created(self, application_name):
        super(LocalDeploymentEndpoint, self).on_application_created(application_name)

    def list_application_versions(self, application_name):
        super(LocalDeploymentEndpoint, self).list_application_versions(application_name)

    def on_application_version_removed(self, application_name):
        super(LocalDeploymentEndpoint, self).on_application_version_removed(application_name)

    def get_application_path(self, application_name, application_version):
        super(LocalDeploymentEndpoint, self).get_application_path(application_name, application_version)

    def on_application_removed(self, application_name):
        super(LocalDeploymentEndpoint, self).on_application_removed(application_name)


