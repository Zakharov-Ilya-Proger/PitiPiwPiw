FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./

COPY . .

RUN pip install .

CMD ["alembic", "upgrade", "head"]
CMD ["python", "-m", "app.core.default_db"]
