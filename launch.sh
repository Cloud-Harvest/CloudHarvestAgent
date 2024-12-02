#!/bin/bash

# Initialize our own variables
with_mongo=0
with_redis=0
config=0
version=0
image="fionajuneleathers/cloud-harvest-agent"
image_tag="latest"

# Check for --with-mongo, --with-redis, --config, --tag, --image and --help flags
for arg in "$@"
do
    case $arg in
        --with-mongo)
        with_mongo=1
        shift # Remove --with-mongo from processing
        ;;
        --with-redis)
        with_redis=1
        shift # Remove --with-redis from processing
        ;;
        --config)
        config=1
        shift # Remove --config from processing
        ;;
        --tag)
        shift # Remove --tag from processing
        image_tag="$1"  # Assign the next argument as the image tag
        shift # Remove the image tag from processing
        ;;
        --image)
        shift # Remove --image from processing
        image="$1"  # Assign the next argument as the image name
        shift # Remove the image name from processing
        ;;
        --version)
        version=1
        shift # Remove --version from processing
        ;;
        --help)
        echo
        echo "Cloud Harvest Agent"
        echo "Usage: ./launcher.sh [--with-mongo] [--with-redis] [--image] [--tag] [--config] [--rebuild] [--version] [--help]"
        echo
        echo "--with-mongo: Start the application with MongoDB."
        echo "--with-redis: Start the application with Redis."
        echo "--help: Displays this help message and exits."
        echo
        echo "Image Options:"
        echo "--image image: Allows you to specify the Docker image name."
        echo "--tag tag: Allows you to specify the Docker image tag."
        echo
        echo "Configuration:"
        echo "--config: Run the configuration script to create the harvest.json file."
        echo "--rebuild: Deletes the entire contents of the './app' directory. Implies --config."
        echo "--version: Prints the version, commit hash, and branch name then exits."
        echo
        exit 0
        ;;
        *)
        shift # Remove generic argument from processing
        ;;
    esac
done

# If --version was provided, print the version from /src/meta.json
if [ $version -eq 1 ]; then
    version_info=$(docker run --rm \
    --entrypoint=/bin/bash \
    "$image:$image_tag" \
    -c "version_number=\$(grep '\"version\"' /src/meta.json | cut -d '\"' -f 4 | tr -d '\n'); \
        commit_hash=\$(cd /src && git rev-parse --short HEAD); \
        branch_name=\$(cd /src && git rev-parse --abbrev-ref HEAD); \
        echo \"\$version_number-\$commit_hash(\$branch_name)\"")
    echo "CloudHarvestAgent v$version_info"
    exit 0
fi

# Check if the app/harvest.json file exists or --config is provided
if [ ! -f "./app/harvest.json" ] || [ $config -eq 1 ]; then
    # If the file does not exist or --config is provided, start config.py using docker run
    docker run -it --rm \
        -v "./app:/src/app" \
        --entrypoint=/bin/bash \
        --user "$(id -u):$(id -g)" \
        "$image:$image_tag" \
        -c "
          source /venv/bin/activate &&
          python3 config.py
          "

    # Check the exit status of config.py
    if [ $? -eq 0 ]; then
        echo "Configuration completed successfully."
    else
        # If the exit status is not 0, abort the script
        echo "config.py exited with an error. Aborting."
        exit 1
    fi

    # If --config was provided, exit with a status code of 0
    if [ $config -eq 1 ]; then
        echo "--config was specified. Exiting."
        exit 0
    fi
fi

if [ ! -d "./app/logs" ] || [ ! -f "./app/logs/agent.log" ]; then
    echo "Creating log directory and log file."
    mkdir -p ./app/logs
    touch ./app/logs/agent.log
fi

export LOCAL_UID=$(id -u)
export LOCAL_GID=$(id -g)
export IMAGE_NAME=$image
export IMAGE_TAG=$image_tag

echo "Starting CloudHarvestAgent with image $image:$image_tag"

# Check the value of with_mongo and with_redis
if [ $with_mongo -eq 1 ] && [ $with_redis -eq 1 ]; then
    docker compose up
elif [ $with_mongo -eq 1 ]; then
    docker compose up harvest-agent mongo
elif [ $with_redis -eq 1 ]; then
    docker compose up harvest-agent redis
else
    docker compose up harvest-agent
fi
