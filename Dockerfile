ARG BASE_IMAGE=alpine:3.20.3
FROM $BASE_IMAGE

# install python
RUN apk add --no-cache python3 py3-flask py3-requests

# add webserver
ADD files/webhook.py webhook.py

# start flask
ENTRYPOINT ["python3", "webhook.py"]
