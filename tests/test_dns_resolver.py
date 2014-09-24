from flexmock import flexmock
from mfcloud.dns_resolver import Resolver
import pytest
from twisted.internet import defer
from twisted.names import dns

@pytest.inlineCallbacks
def test_resolve_unknown_domain():
    resolver = Resolver(servers=[('8.8.8.8', 53)])

    flexmock(resolver)
    resolver.should_receive('_lookup').never()

    #redis
    redis = flexmock()
    redis.should_receive('hget').with_args('domain', 'boo').and_return(None)

    resolver.server_factory = flexmock(redis=redis)

    # resolve unknown domain
    result = yield resolver.lookupAddress('boo')

    assert result == ([], [], [])


@pytest.inlineCallbacks
def test_resolve_unknown_domain_local():
    resolver = Resolver(servers=[('8.8.8.8', 53)], prefix='local')

    flexmock(resolver)
    resolver.should_receive('_lookup').never()

    #redis
    redis = flexmock()
    redis.should_receive('hget').with_args('domain', 'boo.local').and_return(defer.succeed('127.0.0.3'))

    resolver.server_factory = flexmock(redis=redis)

    # resolve unknown domain
    result = yield resolver.lookupAddress('boo.local')

    assert isinstance(result[0][0], dns.RRHeader)
    assert isinstance(result[0][0].payload, dns.Record_A)
    assert result[0][0].payload.dottedQuad() == '127.0.0.3'

@pytest.inlineCallbacks
def test_resolve_unknown_domain_local_unknown():
    resolver = Resolver(servers=[('8.8.8.8', 53)], prefix='local')

    flexmock(resolver)
    resolver.should_receive('_lookup').never()

    #redis
    redis = flexmock()
    redis.should_receive('hget').with_args('domain', 'boo.local').and_return(defer.succeed(None))

    resolver.server_factory = flexmock(redis=redis)

    # resolve unknown domain
    result = yield resolver.lookupAddress('boo.local')

    assert result[0] == []