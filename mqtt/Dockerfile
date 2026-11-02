FROM python:3.12-alpine
WORKDIR /app
RUN apk add --no-cache ca-certificates && pip install --no-cache-dir paho-mqtt==2.1.0
COPY subscriber.py .
CMD ["python", "-u", "subscriber.py"]
