FROM python:3.9-buster

WORKDIR /root/fireprox
COPY . .
RUN pip3 install -r requirements.txt

ENTRYPOINT ["python", "/root/fireprox/fire.py"]
