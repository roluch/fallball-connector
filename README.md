# Fallball connector

This is a basic sample connector for the [Fallball Cloud Storage](https://github.com/ingrammicro/fallball-service).

[![Build Status](https://travis-ci.org/ingrammicro/fallball-connector.svg?branch=master)](https://travis-ci.org/ingrammicro/fallball-connector)
[![codecov](https://codecov.io/gh/ingrammicro/fallball-connector/branch/master/graph/badge.svg)](https://codecov.io/gh/ingrammicro/fallball-connector)

## Running on localhost with tunnel

* Download and unzip fallball-connector

* Install package and requirements for local development

```bash
python setup.py develop
```

* Update `config.yml` file with your credentials

```yaml
fallball_service_url: PUT_HERE_FALLBALL_SERVICE_URI
fallball_service_authorization_token: PUT_HERE_FALLBALL_SERVICE_AUTHORIZATION_TOKEN
oauth_key: PUT_HERE_OAUTH_KEY
oauth_secret: PUT_HERE_OAUTH_SECRET
```

* Run application

```bash
$ python connector/app.py
 * Running on http://0.0.0.0:5000/ (Press CTRL+C to quit)
```

* Create HTTP tunnel with [ngrok](https://ngrok.io)

```bash
ngrok http 5000
```

* Use public connector URL <https://YOUR_UNIQ_ID.ngrok.io/connector/>

If you run the connector without SSL behind SSL-enabled reverse proxy, make sure that proxy populates the `X-Forwarded-Proto` header.

## Running in Docker

```bash
docker-compose up
```

Application is started in debug mode in docker container on port 5000.

## Development

* Run unit tests

```bash
python setup.py nosetests
```

## Logging

Our standard logger outputs in JSON format. You can use it like this:

```python
from connector.utils import logger
logger.info("I am a log entry")
```

It will place into the standard output something similar to this:

```json
{
    "message": "I am a log entry",
    "time": "2017-01-01 10:00:00.270976",
    "level": "INFO",
    "reseller_id": "None"
}
```


#### Using your own logger

If you would like to use your own logger instead, you are welcome to do so.
All python logging utilities are fully supported.

For example:

```python
import sys
import logging

# Optional configuration.
# Here we explicitly instruct logger to always write to stdout,
# even for log levels below ERROR, and configure a logging format.
stream = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream.setFormatter(formatter)

my_logger = logging.getLogger(__name__)
my_logger.setLevel(logging.DEBUG)
my_logger.addHandler(stream)

```

If you use this logger inside HealthCheck handler:

```python
class HealthCheck(ConnectorResource):
    def get(self):
        my_logger.info("I am a log entry")
        return {'status': 'ok',
                'version': version}
```

, you will get an output similar to the one below:

```
2017-08-28 15:05:57,829 - connector.v1.resources.application - INFO - I am a log entry
```


#### Disabling the built-in logger

By default connector logs detailed information about incoming and outgoing requests in JSON format.
It can be distracting during local development.
To turn these logs off, find the following entry in the `connector/utils.py` file:

```python
logger.setLevel(logging.DEBUG)
```
, and change it from `logging.DEBUG` to `logging.CRITICAL`.

This will disable the built-in request and response logs.
Your custom logger will continue to work.