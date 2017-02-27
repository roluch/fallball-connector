import logging
import sys
import socket

from flask import Flask, jsonify
from werkzeug.contrib.fixers import ProxyFix

from connector.config import Config, check_configuration
from connector.v1 import api_bp as api_v1

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream = logging.StreamHandler(sys.stdout)
logger.addHandler(stream)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

app.register_blueprint(api_v1, url_prefix='/v1')


@app.route('/')
def home():  # pragma: no cover
    return jsonify({'service': 'fallball_connector', 'host': socket.gethostname()})


if __name__ == '__main__':
    logger.info(" * Using CONFIG_FILE=%s", Config().conf_file)  # pragma: no cover

    if not check_configuration(Config()):  # pragma: no cover
        raise RuntimeError("You can't run your connector with default "
                           "parameters, please update the JSON config "
                           "file and replace PUT_HERE_* values with real "
                           "ones")

    app.run(debug=True if Config().loglevel == 'DEBUG' else False,
            host='0.0.0.0')  # pragma: no cover
