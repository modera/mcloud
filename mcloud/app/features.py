from cratis.features import Feature
from django.conf.urls import patterns, include, url
import os


class McloudManager(Feature):
    def configure_settings(self):
        self.append_apps(['mcloud.app', 'django_ace', 'mcloud.app.pki'])

        self.settings.STATICFILES_DIRS += (os.path.dirname(__file__) + '/pki/media',)


    def configure_urls(self, urls):

        urls += patterns('',
            (r'^', include('mcloud.app.pki.urls', namespace='pki')),
        )