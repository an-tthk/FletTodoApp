FROM python:3-alpine

WORKDIR /app

COPY requirements.txt ./

RUN apk update && \
	apk add pkgconfig && \
	apk add --no-cache gcc musl-dev mariadb-dev mariadb-connector-c-dev && \
	pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "./main.py"]