FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ARG VERSION=local
ENV APP_VERSION=$VERSION
CMD ["python", "main.py"]