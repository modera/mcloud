

from mfcloud import txhttp
import pytest


@pytest.inlineCallbacks
def test_basic_connect():

    r = yield txhttp.get('http://google.com')

    assert r.code == 200


