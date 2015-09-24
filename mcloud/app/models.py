
from __future__ import unicode_literals

from django.db import models

from django.utils.translation import ugettext_lazy as _
from django_ace import AceWidget
from mcloud.config import YamlConfig
from mcloud.django_adapter import TwistedModel
from mcloud.txdocker import DockerTwistedClient
import os
from twisted.internet import defer


class YamlFancyField(models.TextField):

    def formfield(self, **kwargs):
        kwargs["widget"] = AceWidget(mode='yaml')
        return super(YamlFancyField, self).formfield(**kwargs)


from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^mcloud.app"])

class BaseModel(TwistedModel):

    date_created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    date_updated = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        abstract = True

# {
#     "tls": false,
#     "exports": {
#         "grandex.foo": {
#             "public_app": "grandex24",
#             "public_service": null,
#             "custom_port": null
#         }
#     },
#     "name": "local",
#     "key": null,
#     "default": null,
#     "cert": null,
#     "ca": null,
#     "local": true,
#     "host": "unix://var/run/docker.sock/",
#     "port": null
# }


class Deployment(BaseModel):

    name = models.CharField(max_length=255, verbose_name=_('Name'))
    host = models.CharField(max_length=255, verbose_name=_('Host'), default='unix://var/run/docker.sock/', null=True, blank=True)
    port = models.SmallIntegerField(verbose_name=_('Port'), null=True, blank=True)

    default = models.BooleanField(default=False)
    local = models.BooleanField(default=True)
    tls = models.BooleanField(default=False)

    key = models.TextField(blank=True, null=True)
    cert = models.TextField(blank=True, null=True)
    ca = models.TextField(blank=True, null=True)

    def update(self, exports=None, host=None, local=None,  port=None, tls=False, ca=None, cert=None, key=None):
        if exports:
            self.exports = exports

        if host:
            self.host = host

        if local is not None:
            self.local = local

        if port is not None:
            self.port = port

        if tls is not None:
            self.tls = tls

        if ca is not None:
            self.ca = ca or None

        if cert is not None:
            self.cert = cert or None

        if key is not None:
            self.key = key or None

    def get_client(self):
        if hasattr(self, 'client'):
            return self.client

        if self.local:
            url = self.host
        else:
            scheme = 'https' if self.tls else 'http'
            port = self.port or '2375'
            url = '%s://%s:%s' % (scheme, self.host, port)

        self.client = DockerTwistedClient(url=url.encode())
        return self.client


    @property
    def config(self):
        return {
            'name': self.name,
            'default': self.default,
            'exports': {},
            'host': self.host,
            'port': self.port,
            'tls': self.tls,
            'local': self.local,
            'ca': self.ca,
            'key': self.key,
            'cert': self.cert
        }

    def load_data(self, *args, **kwargs):
        return defer.succeed(self.config)

    def __unicode__(self):
        return self.name
    #
    # class Meta:
    #     verbose_name = _('Deployment')
    #     verbose_name_plural = _('Deployments')

#
# class DeploymentWebBinding(BaseModel):
#     deployment = models.ForeignKey(Deployment)
#


class Application(BaseModel):
    name = models.CharField(max_length=255, verbose_name=_('Name'), default='My app', unique=True)
    path = models.CharField(max_length=255, verbose_name=_('Path'))
    deployment = models.ForeignKey(Deployment, null=True)
    env = models.CharField(max_length=10, verbose_name=_('Environment name'), null=True, blank=True, default='dev')

    source = models.TextField(blank=True, null=True)

    source = YamlFancyField(blank=True, null=True)

    APP_REGEXP = '[a-z0-9\-_]+'
    SERVICE_REGEXP = '[a-z0-9\-_]+'

    #host_ip = inject.attr('host_ip')

    def get_env(self):
        if 'env' in self.config and self.config['env']:
            env = self.config['env']
        else:
            env = 'dev'
        return env

    @defer.inlineCallbacks
    def get_deployment(self):
        return self.deployment

    @defer.inlineCallbacks
    def get_client(self):
        deployment = yield self.get_deployment()
        client = yield deployment.get_client()
        defer.returnValue(client)


    @defer.inlineCallbacks
    def load(self, need_details=False):

        if 'source' in self.config:
            yaml_config = YamlConfig(source=self.config['source'], app_name=self.name, path=self.config['path'], env=self.get_env())
        elif 'path' in self.config:
            yaml_config = YamlConfig(file=os.path.join(self.config['path'], 'mcloud.yml'), app_name=self.name, path=self.config['path'])
        else:
            self.error = {
                'msg': 'Can not parse config'
            }
            defer.returnValue(None)

        deployment = yield self.get_deployment()

        if not deployment:
            self.error = {
                'msg': 'No deployment found'
            }
        else:
            client = deployment.get_client()

            yield yaml_config.load(client=client)



        yield defer.gatherResults([service.inspect() for service in yaml_config.get_services().values()])


        if need_details:
            defer.returnValue(self._details(yaml_config, deployment))
        else:
            defer.returnValue(yaml_config)



    def _details(self, app_config, deployment):
        is_running = True
        status = 'RUNNING'
        errors = []

        web_ip = None
        web_port = None
        web_target = None
        web_service = None

        ssl_ip = None
        ssl_port = None
        ssl_target = None
        ssl_service = None

        full_stats = {}

        services = []
        for service in app_config.get_services().values():
            service.app_name = self.name

            stats = service.stats

            if stats:
                for key, val in stats.items():
                    if not key in full_stats:
                        full_stats[key] = 0
                    full_stats[key] += val

            services.append({
                'shortname': service.shortname,
                'name': service.name,
                'ip': service.ip(),
                'error': service.error,
                'ports': service.public_ports(),
                'hosts_path': service.hosts_path(),
                'volumes': service.attached_volumes(),
                'started_at': service.started_at(),
                'fullname': '%s.%s' % (service.name, self.dns_search_suffix),
                'is_web': service.is_web(),
                'running': service.is_running(),
                'created': service.is_created(),
                'stats': stats,
            })

            if service.is_running():
                if service.is_web():
                    web_ip = service.ip()
                    web_port = service.get_web_port()
                    web_target = '%s:%s' % (service.ip(), service.get_web_port())
                    web_service = service.name

                if service.is_ssl():
                    ssl_ip = service.ip()
                    ssl_port = service.get_ssl_port()
                    ssl_target = '%s:%s' % (service.ip(), service.get_ssl_port())
                    ssl_service = service.name

            else:
                is_running = False

                if not service.error:
                    status = 'STOPPED'
                else:
                    status = 'error'
                    errors.append('%s: %s' % (service.name, service.error))



        return {
            'name': self.name,
            'deployment': deployment.name,
            'hosts': app_config.hosts,
            'volumes': app_config.get_volumes(),
            'fullname': '%s.%s' % (self.name, self.dns_search_suffix),
            'web_ip': web_ip,
            'web_port': web_port,
            'web_target': web_target,
            'web_service': web_service,
            'ssl_ip': ssl_ip,
            'ssl_port': ssl_port,
            'ssl_target': ssl_target,
            'ssl_service': ssl_service,
            'public_urls': self.public_urls,
            'config': self.config,
            'services': services,
            'stats': full_stats,
            'running': is_running,
            'status': status,
            'errors': errors,
        }
