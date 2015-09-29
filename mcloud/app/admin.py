from __future__ import unicode_literals
from django.contrib import admin
from mcloud.app.models import Deployment, Application, Service


class DeploymentAdmin(admin.ModelAdmin):
    list_display = ('name', 'default', 'host', 'port', 'tls')
    search_fields = ('name', )

admin.site.register(Deployment, DeploymentAdmin)


class ServiceInline(admin.StackedInline):
    model = Service

    suit_classes = 'suit-tab suit-tab-service'


class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'deployment', 'env')
    search_fields = ('name', )

    fieldsets = (
        (None, {
            'classes': ('suit-tab suit-tab-general',),
            'fields': ('name',  'deployment', 'env')
        }),
    )

    suit_form_tabs = (
        ('general', 'General'),
        ('service', 'Services'),
    )

    inlines = [ServiceInline]

admin.site.register(Application, ApplicationAdmin)

