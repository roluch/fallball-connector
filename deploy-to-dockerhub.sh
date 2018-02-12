#!/usr/bin/env bash
VERSION=`cat VERSION`
REPO=ingrammicrocloud/fallball-connector

docker build -t $REPO .
docker tag $REPO $REPO:latest
docker tag $REPO $REPO:$VERSION
docker login -u="$DOCKER_USERNAME" -p="$DOCKER_PASSWORD"
docker push $REPO