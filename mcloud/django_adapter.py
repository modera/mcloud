

from .django.db import connections as django_connections
from .django.db.models import Manager
from twisted.enterprise import adbapi

from .django.db.models.query import QuerySet
from .django.db.models.sql.query import Query


class TwistedConnections:
    def __init__(self):
        self.databases = django_connections.databases
        self._connections = {}

    def __getitem__(self, alias):
        if alias in self._connections:
            return self._connections[alias]
        django_connections.ensure_defaults(alias)
        db = self.databases[alias]
        connection = adbapi.ConnectionPool(db['ENGINE'], db['NAME'], db['USER'], db['PASSWORD'])
        self._connections[alias] = connection
        return connection

    def __iter__(self):
        return iter(self.databases)

    def all(self):
        return [self[alias] for alias in self]

connections = TwistedConnections()


class TwistedQuery(Query):
    def twisted_compiler(self, using=None, connection=None):
        if using is None and connection is None:
            raise ValueError("Need either using or connection")
        if using:
            connection = connections[using]
        else:
            connection = connections[connection.alias]
        # Check that the compiler will be able to execute the query
        for alias, aggregate in list(self.aggregate_select.items()):
            connection.ops.check_aggregate_support(aggregate)

        return connection.ops.compiler(self.compiler)(self, connection, using)

from twisted.internet import reactor

class TwistedQuerySet(QuerySet):
    def __init__(self, model=None, query=None, using=None):
        query = query or TwistedQuery(model)
        super(TwistedQuerySet, self).__init__(model=model, query=query, using=using)
        self.success_callback = None
        self.error_callback = None

    def twist(self):
        """
        Use twisted database api to run the query and return the raw results in a deferred
        """
        query = self.query
        assert(isinstance(query, Query))
        compiler = query.get_compiler(self.db)
        sql, params = compiler.as_nested_sql()
        if not sql:
            return
        connection = connections[self.db]
        return connection.runQuery(sql, params)

    def _super_threaded(self, function_name_to_call__, *args, **kwargs):
        return reactor.callInThread(getattr(super(TwistedQuerySet, self), function_name_to_call__), *args, **kwargs)

    def _clone(self, klass=None, setup=False, **kwargs):
        self.success_callback = kwargs.pop('success_callback', self.success_callback)
        self.error_callback = kwargs.pop('error_callback', self.error_callback)
        clone = super(TwistedQuerySet, self)._clone(klass, setup, **kwargs)
        return clone

    def all(self, **kwargs):
        return self._super_threaded('all', **kwargs)

    def none(self, **kwargs):
        return self._super_threaded('none', **kwargs)

    def count(self, **kwargs):
        return self._super_threaded('count', **kwargs)

    def get(self, *args, **kwargs):
        return self._super_threaded('get', *args, **kwargs)

    def get_or_create(self, **kwargs):
        return self._super_threaded('get_or_create', **kwargs)

    def delete(self, **kwargs):
        return self._super_threaded('delete', **kwargs)

    def update(self, values, **kwargs):
        return self._super_threaded('update', values, **kwargs)

    def in_bulk(self, id_list, **kwargs):
        return self._super_threaded('in_bulk', id_list, **kwargs)

from .django.db import models

class TwistedManager(models.Manager):
    queryset_class = TwistedQuerySet

    def get_query_set(self):
        return self.queryset_class(self.model, using=self._db)



class TwistedModel(models.Model):
    objects = Manager()
    tx = TwistedManager()

    class Meta:
        abstract = True