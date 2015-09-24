from cratis.features import Feature
from django.conf.urls import patterns, include, url



class McloudManager(Feature):
    def configure_settings(self):
        self.append_apps(['mcloud.app', 'django_ace'])
