# coding=utf-8
from mcloud.app.features import McloudManager
from os.path import abspath, dirname, join, normpath

from cratis.settings import CratisConfig
from cratis_base.features import Common, Debug
from cratis_admin.features import AdminArea
from cratis_admin_suit.features import AdminThemeSuit

import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

class Dev(CratisConfig):
    DEBUG = True

    LOGGING = {
        'version': 1,
        'root': {
            'level': 'INFO',
            'handlers': ['console']
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler'
            },
        },

    }

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'mcloud',
            'USER': 'mcloud',
            'PASSWORD': '123123',
            'HOST': '127.0.0.1',
        },
    }

    DJANGO_ROOT = dirname(dirname(abspath(__file__)))

    LOCALE_PATHS = (
        os.path.join(BASE_DIR, 'locale'),
    )

    SITE_ROOT = dirname(DJANGO_ROOT)

    FEATURES = (

        # Debug(),

        Common(sites_framework=True),

        AdminThemeSuit(title='Mcloud Server'),

        # AdminThemeSuit(title='Mcloud admin', menu=(

            # {'label': u'Документы', 'icon': ' icon-folder-open', 'models': (
            #     # {'model': 'filer.folderpermission', 'permissions': ('ticcet_admin',)},
            #     'filer.folder',
            #
            # )},
            # # {'label': 'Monitoring', 'icon': ' icon-headphones', 'permissions': ('ticcet_admin',), 'models': (
            # #     'djcelery.taskstate',
            # # )},
            # {'label': u'Пользователи', 'icon': 'icon-user', 'models': (
            #     'auth.group',
            #     'auth.user',
            #     # 'cratis_rules.ruletype',
            #     # 'cratis_rules.rule',
            # )},
            # {'label': u'Лизинг', 'app': 'car'},
            # {'label': u'Контент', 'icon': 'icon-map-marker', 'app': 'main'},
            # {'label': u'Раегиональные настройки', 'icon': 'icon-map-marker', 'app': 'cratis_shop_regions'},
            # {'label': u'Платежи', 'icon': 'icon-map-marker', 'app': 'cratis_shop_payment'},
            # {'label': u'Магазин', 'icon': 'icon-map-marker', 'app': 'shop'},
            # {'label': u'Настройки анкеты', 'icon': 'icon-map-marker', 'models': (
            #     'portfolio.orderroomtypequestion',
            #     'portfolio.roomtype',
            #     'portfolio.wizardpagegroup',
            #     'portfolio.wizardpage',
            #     'portfolio.buildingtype',
            #     'portfolio.buildingcompany',
            #     'service.price',
            #
            # )},
            # {'label': u'Заказы', 'icon': 'icon-map-marker', 'models': (
            #     'portfolio.order',
            #     'portfolio.ordervariant',
            #     'portfolio.ordervariantvisualisation',
            #     'portfolio.portfolio',
            #     'portfolio.gallery',
            # )},

        # )),
        AdminArea(prefix='manager'),
        # Debug(),

        McloudManager()
    )

    # EMAIL_HOST = 'postfix'

    # EMAIL_FROM = 'info@grandex24.ee'

    SECRET_KEY = 'testing_only'

    DATETIME_FORMAT = 'd.m.Y H:m'

    # AUTHENTICATION_BACKENDS = ('main.common.UsernameOrEmailAuthBackend',)

    # CACHES = {
    #     'default' : dict(
    #         BACKEND = 'redis_cache.RedisCache',
    #         LOCATION = 'redis:6379',
    #         # JOHNNY_CACHE = True,
    #     )
    # }
    # JOHNNY_MIDDLEWARE_KEY_PREFIX='jc_myproj'



class Test(Dev):
    TEMPLATE_DEBUG = False


class Prod(Dev):
    TEMPLATE_DEBUG = True
    # COMPRESS_ENABLED = True
    SECRET_KEY = 'djshkdhsjfhskdf'
    #DEBUG = False

    LOGGING = {
        'version': 1,
        'root': {
            'level': 'INFO',
            'handlers': ['console']
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler'
            },
        },

    }

    # EMAIL_HOST = 'email-smtp.eu-west-1.amazonaws.com'
    # EMAIL_HOST_USER = 'AKIAJIUE5AVXBR2UY4RA'
    # EMAIL_HOST_PASSWORD = 'Aqt8SfjW0C0P+Oe90uTOGKBhPVj8PBbQrDQzIjh12fjX'
    # EMAIL_USE_TLS = True

    DEBUG = True
    ALLOWED_HOSTS = ['*']

    # DATABASES = {
    #     'default': {
    #         'ENGINE': 'django.db.backends.mysql',
    #         'NAME': 'grandex24',
    #         'USER': os.environ.get('OPENSHIFT_MYSQL_DB_USERNAME'),
    #         'PASSWORD': os.environ.get('OPENSHIFT_MYSQL_DB_PASSWORD'),
    #         'HOST': os.environ.get('OPENSHIFT_MYSQL_DB_HOST'),
    #         'PORT': os.environ.get('OPENSHIFT_MYSQL_DB_PORT')
    #     },
    # }


    STATIC_ROOT = os.path.join(Dev.DJANGO_ROOT, 'wsgi','static')
#
# Prod.add_feature(
#     Sentry(dsn='https://7d7bb771ac7b44819b3215df4decf3ed:409ceb01224645afa37b09ff7b98a164@app.getsentry.com/30306')
# )
