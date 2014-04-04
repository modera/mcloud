import docker
from mfcloud.container import DockerLocal
from mfcloud.service import Service
from mfcloud.util import real_docker


def test_docker_local():

    with real_docker():
        d = DockerLocal()

        assert isinstance(d.client, docker.Client)
        print d.client.info()

        assert d.client.info()['Driver'] == 'aufs', 'Drivers other than aufs are not tested'


def test_gen_wrapper():
    """
    Tests how well works generator for workaround.
    """

    def broken_generator():

        for x in range(1, 4):
            if x < 3:
                yield x
            else:
                raise ValueError()

    vals = [x for x in DockerLocal._gen_wrapper(broken_generator())]

    assert vals == [1, 2]


#def test_start_container():
#
#    with real_docker():
#
#        s = Service()
#        s.image_builder =
#
#
#        d = DockerLocal()
#
#
#
#        #
#        #for x in stream:
#        #    print x
#
#        #builder =
#
#        image_name = d.build_image()
##
