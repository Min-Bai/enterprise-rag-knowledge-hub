FROM docker.m.daocloud.io/library/python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_DEFAULT_TIMEOUT=120

COPY requirements.txt .
COPY docker/wheels/ /tmp/torch-wheels/
RUN --mount=type=cache,target=/root/.cache/pip \
    if ls /tmp/torch-wheels/*.whl >/dev/null 2>&1; then \
      pip install --no-deps /tmp/torch-wheels/*.whl; \
    else \
      pip install --index-url https://download.pytorch.org/whl/cpu torch==2.5.1+cpu; \
    fi && \
    grep -v '^torch==' requirements.txt > /tmp/requirements-no-torch.txt && \
    pip install -r /tmp/requirements-no-torch.txt

COPY python_practice ./python_practice
COPY scripts ./scripts

EXPOSE 8000

CMD ["uvicorn", "python_practice.day57.main:app", "--host", "0.0.0.0", "--port", "8000"]
