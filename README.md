Fallball connector
=====
[![Build Status](https://travis-ci.org/odin-public/fallball-connector.svg?branch=master)](https://travis-ci.org/odin-public/fallball-connector)
[![Coverage Status](https://coveralls.io/repos/github/odin-public/fallball-connector/badge.svg)](https://coveralls.io/github/odin-public/fallball-connector)

This is a basic sample connector for the FallBall cloud storage service.

Before you start it, in `connector/config.json` replace default 
values with values from your application.
Specifically, resource names from your application's model, 
URL where FallBall application is deployed (`base_uri` parameter), 
FallBall application token (`application_token` parameter),
and your connector's OAuth client key and secret.

### Running in Docker
To run with docker, just run this in the project folder:

    docker-compose up
    
Application is started in debug mode in docker container.

### Running without Docker
Before using it install the requirements from `requirements.txt`:

    pip install -r requirements.txt

It's a flask application, to run it simply start `app.py` from the `connector` package:
    
    python app.py
    
To run with debug enabled, set the `DEBUG` environment variable:
    
    DEBUG=True python app.py


If you run connector without SSL behind SSL-enabled reverse proxy, set REVERSE_PROXIED env variable.
It will reconfigure the application to use correct schema in requests (https), needed to preserve OAuth signatures.
Check sample nginx config in `utils.py`.