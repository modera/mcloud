# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Deployment.enabled'
        db.delete_column(u'app_deployment', 'enabled')

        # Adding field 'Deployment.host'
        db.add_column(u'app_deployment', 'host',
                      self.gf('django.db.models.fields.CharField')(default=u'unix://var/run/docker.sock/', max_length=255),
                      keep_default=False)

        # Adding field 'Deployment.port'
        db.add_column(u'app_deployment', 'port',
                      self.gf('django.db.models.fields.SmallIntegerField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Deployment.default'
        db.add_column(u'app_deployment', 'default',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Deployment.local'
        db.add_column(u'app_deployment', 'local',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)

        # Adding field 'Deployment.tls'
        db.add_column(u'app_deployment', 'tls',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Deployment.key'
        db.add_column(u'app_deployment', 'key',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Deployment.cert'
        db.add_column(u'app_deployment', 'cert',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Deployment.ca'
        db.add_column(u'app_deployment', 'ca',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Adding field 'Deployment.enabled'
        db.add_column(u'app_deployment', 'enabled',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Deleting field 'Deployment.host'
        db.delete_column(u'app_deployment', 'host')

        # Deleting field 'Deployment.port'
        db.delete_column(u'app_deployment', 'port')

        # Deleting field 'Deployment.default'
        db.delete_column(u'app_deployment', 'default')

        # Deleting field 'Deployment.local'
        db.delete_column(u'app_deployment', 'local')

        # Deleting field 'Deployment.tls'
        db.delete_column(u'app_deployment', 'tls')

        # Deleting field 'Deployment.key'
        db.delete_column(u'app_deployment', 'key')

        # Deleting field 'Deployment.cert'
        db.delete_column(u'app_deployment', 'cert')

        # Deleting field 'Deployment.ca'
        db.delete_column(u'app_deployment', 'ca')


    models = {
        u'app.deployment': {
            'Meta': {'object_name': 'Deployment'},
            'ca': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'cert': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'date_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'host': ('django.db.models.fields.CharField', [], {'default': "u'unix://var/run/docker.sock/'", 'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'local': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tls': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['app']