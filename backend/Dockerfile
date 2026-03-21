FROM python:3.11

WORKDIR /app

RUN apt-get update && apt-get install -y poppler-utils

COPY . .

RUN pip install -r requirements.txt

CMD ["sh", "start.sh"]