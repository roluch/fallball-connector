FROM python:2.7
ADD ./connector /connector
ADD ./requirements.txt /connector/requirements.txt
WORKDIR /connector
ENV PYTHONPATH /
ENV CONNECTOR_PORT 80
ENV DEBUG True
RUN pip install -r requirements.txt
EXPOSE 80
ENTRYPOINT ["python"]
CMD ["app.py"]
