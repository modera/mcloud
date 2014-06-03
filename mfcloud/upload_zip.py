import argparse
from flask import Flask, request
import os
from datetime import timedelta
from flask import make_response, current_app
from functools import update_wrapper
from mfcloud.archive import ArchiveFile
import json

app = Flask(__name__)


def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator


@app.route('/', methods=['GET', 'POST', 'OPTIONS'])
@crossdomain(origin='*')
def upload_file():
    if request.method == 'POST':
        f = request.files['file']
        register_id = request.form.get("register_id")
        path = os.path.dirname(os.path.abspath(__file__))
        folder = "{0}/archives/{1}/".format(path, register_id)
        if not os.path.isdir(folder):
            os.mkdir(folder)
        filename = f.filename
        path = "{0}/{1}".format(folder, filename)
        f.save(path)

        archive = ArchiveFile(path, folder)
        archive.extract()

        folder_archive = filename.split(".zip")
        if os.path.isfile("{0}unzip/{1}/mfcloud.yml".format(folder, folder_archive[0])):
            return json.dumps({"status": "ok", "path": "{0}unzip/{1}/".format(folder, folder_archive[0])})
        else:
            return json.dumps({"status": "{0}unzip/{1}/mfcloud.yml".format(folder, folder_archive[0]), "message": "Archive have not correct format"})


def entry_point():

    parser = argparse.ArgumentParser(description='Dns resolver')

    parser.add_argument('--port', type=int, default=5000, help='port number')
    parser.add_argument('--interface', type=str, default='0.0.0.0', help='ip address')

    args = parser.parse_args()

    app.run(debug=True, port=args.port, host=args.interface)

if __name__ == '__main__':
    entry_point()
