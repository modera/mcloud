from flask import Flask
app = Flask(__name__)

from redis import Redis
redis = Redis(host='redis')

@app.route("/")
def hello():
    return "Hello World!"

@app.route("/inc")
def incr():

    i = redis.incr('foo')
    return "Hello World! %s" % i

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)
