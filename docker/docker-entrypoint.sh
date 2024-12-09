#!/bin/bash

# Make the configuration directory for the app
mkdir -pv /src/app/logs

# Copy the configuration file to the app directory
cp -nv /src/harvest.yaml /src/app/harvest.yaml

# Perform the following actions:
# 1. Activate the virtual environment
# 2. Generate the plugins.txt file
# 3. Install the plugins
# 4. Start the application
source /venv/bin/activate \
&& /src/docker/make_plugins.txt.py \
&& touch -a /src/app/plugins.txt \
&& pip install -r /src/app/plugins.txt \
&& python /src/CloudHarvestAgent
