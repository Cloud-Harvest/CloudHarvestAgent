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
host="0.0.0.0"
port="8500"
pemfile="$base_path/app/harvest-self-signed.pem"
debug=0
workers=1

# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --host) host="$2"; shift ;;
        --port) port="$2"; shift ;;
        --pemfile) pemfile="$2"; shift ;;
        --debug) debug=1 ;;
        --workers) workers="$2"; shift ;;
        --help)
            # Echo the launcher script's help message
            echo "$app_name Usage: [options]"
            echo
            echo "Options:"
            echo "  --host <host>        Host to bind to (default: $host)"
            echo "  --port <port>        Port to bind to (default: $port)"
            echo "  --pemfile <file>     Path to the PEM file (default: $pemfile)"
            echo "  --debug              Launches the application using the python interpreter instead of gunicorn"
            echo "  --workers <num>      Number of gunicorn workers (default: $workers)"
            echo "  --help               Show this help message"

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
export "${APP_NAME}_HOST"=$host
export "${APP_NAME}_PORT"=$port
export "${APP_NAME}_PEMFILE"=$pemfile
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
    && echo "Starting Gunicorn with $workers workers..." \
    && gunicorn -w "$workers" -b "$host:$port" --certfile "$pemfile" --keyfile "$pemfile" "$app_name.__main__:app"
fi

echo "$app_name has stopped."
