from __future__ import unicode_literals
from django.contrib import admin
from mcloud.app.models import Deployment, Application


class DeploymentAdmin(admin.ModelAdmin):
    list_display = ('name', 'default', 'host', 'port', 'tls')
    search_fields = ('name', )

admin.site.register(Deployment, DeploymentAdmin)

class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'deployment', 'env')
    search_fields = ('name', )

admin.site.register(Application, ApplicationAdmin)
