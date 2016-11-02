#! /bin/bash
set -xe
export PYTHONUNBUFFERED=1

python3.4 -m flake8
python2.7 -m flake8


cp -r ~/.virtualenvs/fallballconnector-venv .
source fallballconnector-venv/bin/activate

nosetests

deactivate
rm -rf fallballconnector-venv