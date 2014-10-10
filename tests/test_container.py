from flexmock import flexmock
from mcloud.config import YamlConfig
from mcloud.container import ContainerBuider
from mcloud.service import Service

#
# def test_start_container():
#
#    with mock_docker() as docker_mock:
#         dm = docker_mock
#         """@type : flexmock.Mock"""
#
#         # dm.should_receive()
#
#         s = Service()
#         builder = flexmock(IImageBuilder)
#         s.image_builder = builder
#
#         # builder.should_receive('build_image').ordered().once()
#         # builder.should_receive('get_image').ordered().once().and_return('foo')
#         #
#         #
#         # d = DockerLocal()
#         #
#         # d.build_service_container()
# #
# #
# #
# #        #
# #        #for x in stream:
#        #    print x
#
#        #builder =
#
#        image_name = d.build_image()
##
import pytest
from twisted.internet import defer
#
#
#@pytest.inlineCallbacks
#def test_generate_container_config():
#
#    config = flexmock(YamlConfig())
#
#    service = Service(
#        image_builder=flexmock(build_image=lambda: defer.succeed('ubuntu/foo')),
#        name='foo',
#        volumes=[{'foo': 'bar'}],
#        command='some --cmd',
#        env={'baz': 'bar'}
#    )
#
#    builder = ContainerBuider()
#
#    builder.ensure_container_created()
#
#    config = yield service.build_docker_config()
#
#    assert config == {
#     "Hostname":"",
#     "User":"",
#     "Memory":0,
#     "MemorySwap":0,
#     "AttachStdin":False,
#     "AttachStdout":True,
#     "AttachStderr":True,
#     "PortSpecs":None,
#     "Tty":False,
#     "OpenStdin":False,
#     "StdinOnce":False,
#     "Env":None,
#     "Cmd":[
#             "date"
#     ],
#     "Dns":None,
#     "Image":"base",
#     "Volumes":{
#             "/tmp": {}
#     },
#     "VolumesFrom":"",
#     "WorkingDir":"",
#     "ExposedPorts":{
#             "22/tcp": {}
#     }
#}