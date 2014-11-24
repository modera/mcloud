import os
from klein import Klein
from twisted.web.static import File
from pkg_resources import resource_filename

app = Klein()
static_dir = resource_filename(__name__, 'static/')

@app.route('/', branch=True)
def static(request):
    return File(static_dir)

mcloud_web = app.resource