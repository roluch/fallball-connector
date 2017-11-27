FROM python:3.6
ADD ./connector /connector
ADD ./requirements.txt /connector/requirements.txt
WORKDIR /connector
ENV PYTHONPATH /
ENV CONNECTOR_PORT 80
ENV DEBUG True
RUN pip install -r requirements.txt
RUN pip install gunicorn
EXPOSE 80
ENTRYPOINT ["/usr/local/bin/gunicorn", "connector.app:app"]
CMD ["-b", "0.0.0.0:80", "-t", "180", "-w", "4", "-k", "gthread", "--threads", "8"]
