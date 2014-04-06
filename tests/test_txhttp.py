

from mfcloud import txhttp
import pytest


@pytest.inlineCallbacks
def test_basic_connect():

    r = yield txhttp.get('unix://var/run/docker.sock//info')

    assert r.code == 200


