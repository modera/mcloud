from cratis.cli import load_env
import os
from pkg_resources import resource_filename

import django

def init_django():
    os.environ['DJANGO_SETTINGS_MODULE'] = 'mcloud.app.settings'
    os.environ['CRATIS_APP_PATH'] = resource_filename('mcloud', 'app')
    os.environ['DJANGO_CONFIGURATION'] = 'Dev'

    from configurations import importer
    importer.install(check_options=True)

    load_env()

    django.setup()