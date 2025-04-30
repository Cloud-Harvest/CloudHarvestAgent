FROM python:3.13-bookworm AS python

WORKDIR /src

ENV PIP_ROOT_USER_ACTION=ignore

COPY . .

RUN /bin/bash -c " \
        python -m venv /src/venv \
        && source /src/venv/bin/activate \
        && pip install --upgrade pip \
        && pip install setuptools \
        && pip install -r requirements.txt \
        && export PYTHONPATH=/src \
        && python -m unittest discover --verbose -s /src/tests/ \
    "

ENTRYPOINT /bin/bash /src/docker/docker-entrypoint.sh
