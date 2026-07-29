FROM docker.m.daocloud.io/library/python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY python_practice ./python_practice

EXPOSE 8000

CMD ["uvicorn", "python_practice.day57.main:app", "--host", "0.0.0.0", "--port", "8000"]
