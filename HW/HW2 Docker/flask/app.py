from flask import Flask, make_response, request
import os

app = Flask(__name__)

@app.route('/')
def hello():
    response = make_response(
        {
            'response': 'Hello, World!',
            'status': 200
        }
    )
    return response

@app.route('/repeat')
def getInfo():
    input = request.args.get('input', default = 1)
    response = make_response(
        {
            "body": input,
            "status": 200
        }
    )
    return response

@app.route('/health')
@app.route('/healthcheck')
def sysCheck():
    response = make_response(
        {
            "body": "OK",
            "status": 200
        }
    )
    return response

if __name__ == '__main__':
    # By default flask is only accessible from localhost.
    # Set this to '0.0.0.0' to make it accessible from any IP address
    # on your network (not recommended for production use)
    app.run(host='0.0.0.0', debug=True, port = int(os.getenv("PORT")))
