import os
from klein import Klein
from twisted.web.static import File

app = Klein()

base_path = os.path.dirname(__file__)

@app.route('/', branch=True)
def static(request):
    return File(os.path.join(base_path, 'static/'))

mcloud_web = app.resource