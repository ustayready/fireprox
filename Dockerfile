FROM python:3.7-slim

WORKDIR /root/fireprox
COPY . .
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "/root/fireprox/fire.py"]
