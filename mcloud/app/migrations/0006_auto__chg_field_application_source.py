# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Application.source'
        db.alter_column(u'app_application', 'source', self.gf('mcloud.app.models.YamlFancyField')(null=True))

    def backwards(self, orm):

        # Changing field 'Application.source'
        db.alter_column(u'app_application', 'source', self.gf('django.db.models.fields.TextField')(null=True))

    models = {
        u'app.application': {
            'Meta': {'object_name': 'Application'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'date_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'deployment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['app.Deployment']", 'null': 'True'}),
            'env': ('django.db.models.fields.CharField', [], {'default': "u'dev'", 'max_length': '10', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "u'My app'", 'unique': 'True', 'max_length': '255'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'source': ('mcloud.app.models.YamlFancyField', [], {'null': 'True', 'blank': 'True'})
        },
        u'app.deployment': {
            'Meta': {'object_name': 'Deployment'},
            'ca': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'cert': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'date_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'host': ('django.db.models.fields.CharField', [], {'default': "u'unix://var/run/docker.sock/'", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'local': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'port': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tls': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['app']