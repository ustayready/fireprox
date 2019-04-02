FROM python:3.7-alpine
RUN apk add git libxml2-dev libxslt-dev build-base
RUN git clone https://github.com/ustayready/fireprox /root/fireprox
RUN cd /root/fireprox && pip install -r requirements.txt
WORKDIR /root/fireprox
COPY entrypoint.sh /tmp/entrypoint.sh
RUN chmod +x /tmp/entrypoint.sh
ENTRYPOINT ["/tmp/entrypoint.sh"]
