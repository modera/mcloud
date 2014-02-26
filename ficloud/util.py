
def format_service_status(service):
    if len(service.containers()):
        s = []
        for ct in service.containers(stopped=True):
            if ct.is_running:
                s.append('UP[%s]' % (','.join(ct.inspect()['NetworkSettings']['Ports'].keys())))
            else:
                s.append('DOWN')

        service_status = ','.join(s)

    else:
        service_status = 'NO CONTAINERS'
    return service_status

