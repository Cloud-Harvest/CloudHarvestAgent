FROM python:3.13-bookworm AS python

WORKDIR /src

ENV PIP_ROOT_USER_ACTION=ignore

# Install vim and purge apt cache
RUN apt-get update \
    && apt-get install -y vim \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN /bin/bash -c " \
        python -m venv /src/venv \
        && source /src/venv/bin/activate \
        && pip install --upgrade pip \
        && pip install setuptools \
        && pip install . \
        && export PYTHONPATH=/src \
        && python -m unittest discover --verbose -s /src/tests/ \
    "

ENTRYPOINT /bin/bash /src/docker/docker-entrypoint.sh
