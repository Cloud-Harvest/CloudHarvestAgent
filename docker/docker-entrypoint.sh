#!/bin/bash

# Determine the base path
base_path=$(realpath "/src")
if [ ! -d "$base_path" ]; then
    base_path=$(realpath ".")
fi

# Script parameters
app_name="CloudHarvestAgent"
APP_NAME="${app_name^^}"

# Default values for options
debug=0
conf="$base_path/$app_name/gunicorn_conf.py"

# Default values for debug mode options
host="127.0.0.1"
port="8000"
pemfile="$base_path/certs/agent.pem"

# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --conf)
          conf="$2";
          shift ;;
        --debug)
          debug=1
          ;;
        --help)
            # Echo the launcher script's help message
            echo "$app_name Usage: [options]"
            echo
            echo "Options:"
            echo "  --debug              Launches the application using the python interpreter instead of gunicorn"
            echo "  --help               Show this help message"
            echo
            echo "Debug Mode Options"
            echo "  --host <host>        Host to bind the application to (default: $host)"
            echo "  --port <port>        Port to bind the application to (default: $port)"
            echo "  --pemfile <path>    Path to the PEM file for SSL (default: $pemfile)"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Remove command arguments so they are not passed to the application
set --

# Make the configuration directory for the app
subdirs=("logs")
for subdir in "${subdirs[@]}"; do
    mkdir -pv "$base_path/app/$subdir"
done

# Copy the configuration file to the app directory
# Use the -n flag to prevent overwriting the file
cp -nv "$base_path/harvest.yaml" "$base_path/app/harvest.yaml"

# Set environment variables
export PYTHONPATH="$base_path"

# Start the application
if [[ "$debug" -eq 1 ]]; then
    # Debug mode: Pass all parameters to the Python script
    source "$base_path/venv/bin/activate" \
    && echo "Starting in python debug mode..." \
    && python "$base_path/$app_name" --host "$host" --port "$port" --pemfile "$pemfile" --debug
else
    # Production mode: Use Gunicorn
    source "$base_path/venv/bin/activate" \
    && echo "Starting Gunicorn..." \
    && gunicorn -c "$conf" "$app_name.__main__:app"
fi

echo "$app_name has stopped."
