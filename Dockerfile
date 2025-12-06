FROM python:3.13-slim

ARG BASE_DIR=/opt/app

ENV \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

RUN pip install pipx
RUN PIPX_BIN_DIR=/usr/local/bin pipx install poetry==1.8.3

RUN apt-get update && apt-get install

WORKDIR ${BASE_DIR}
COPY ./pyproject.toml ./
RUN poetry install --no-ansi

COPY ./src ./src

ENV PYTHONPATH "$PYTHONPATH:${BASE_DIR}/src/"
WORKDIR ${BASE_DIR}/src

ENV \
    DJANGO_SETTINGS_MODULE=webapp.settings \
    PORT=8000

EXPOSE 8000/tcp

RUN \
    DJ__SECRET_KEY=empty \
    python ./manage.py collectstatic --noinput

ENTRYPOINT ["bash","entrypoint.sh"]
CMD ["gunicorn", "webapp.wsgi", "-w", "4","-b","0.0.0.0:8000"]
