#!/bin/bash

# Source the virtual environment
# Check if the plugins.txt file exists
# Install the plugins
# Run the application

source /venv/bin/activate \
&& touch -a /src/app/plugins.txt \
&& pip install -r /src/app/plugins.txt \
&& python /src/CloudHarvestAgent
