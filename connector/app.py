import logging
import os
import sys
import socket

from flask import Flask, jsonify
from werkzeug.contrib.fixers import ProxyFix

from connector.config import Config, check_configuration
from connector.v1 import api_bp as api_v1

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not Config().debug:  # pragma: no cover
    logging.disable(logging.DEBUG)

stream = logging.StreamHandler(sys.stdout)
logger.addHandler(stream)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

app.register_blueprint(api_v1, url_prefix='/connector/v1')

api_v1.name = 'latest'
app.register_blueprint(api_v1, url_prefix='/connector')


@app.route('/')
def home():
    return jsonify({'service': 'fallball_connector', 'host': socket.gethostname()})


if __name__ == '__main__':
    logger.info(" * Using CONFIG_FILE=%s", Config().conf_file)

    if not check_configuration(Config()):
        raise RuntimeError("You can't run your connector with default "
                           "parameters, please update the YML config "
                           "file and replace PUT_HERE_* values with real "
                           "ones")
    port = int(os.getenv('CONNECTOR_PORT', '5000'))
    app.run(debug=Config().debug, host='0.0.0.0', port=port, threaded=True)
