from flask import Flask, request
from werkzeug import secure_filename
import os

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        f = request.files['file']
        path = "{0}/archives/{1}".format(
            os.path.dirname(os.path.abspath(__file__)), secure_filename(f.filename))
        f.save(path)
        return 'OK'
    return ''

if __name__ == '__main__':
    app.run()
