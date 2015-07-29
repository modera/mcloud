
What is mcloud
===========================





.. uml::

    [Mcloud client] as cli
    [Mcloud server] as srv

    cli .right.> srv : WebsocketAPI


    srv .down.> [Docker1] : RemoteAPI
    srv .down.> [Docker2] : RemoteAPI
    srv .down.> [Docker3] : RemoteAPI

