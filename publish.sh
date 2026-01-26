#!/bin/bash

# publish.sh
# This script is used to build, test, and publish a Docker image for the Cloud Harvest Agent.
# It fetches the version number from pyproject.toml and uses it along with the git commit's short name to tag the Docker image.
# The script also checks that all commits have been pushed to git and that the current branch is main.
#
# Note: This script requires Docker, git, and grep to be installed and properly configured on the system where it will be run.

# Initialize our own variables
dry_run=0
image_name="fionajuneleathers/cloud-harvest-agent"
skip_git_check=0

# Check for --dry-run, --skip-git-check and --help flags
for arg in "$@"
do
    case $arg in
        --dry-run)
        dry_run=1
        shift # Remove --dry-run from processing
        ;;
        --skip-git-check)
        skip_git_check=1
        shift # Remove --skip-git-check from processing
        ;;
        --progress)
        progress="$2"
        shift 2 # Remove --progress and its value from processing
        ;;
        --help)
        echo "Usage: ./publish.sh [--dry-run] [--progress] [--skip-git-check] [--help]"
        echo ""
        echo "Options:"
        echo "--dry-run: Perform all steps except pushing the Docker image to the Docker registry."
        echo "--progress: Change the output format of the build process. Default is plain."
        echo "--skip-git-check: Skip the check for unpushed git commits."
        echo "--help: Show this help message."
        exit 0
        ;;
        *)
        shift # Remove generic argument from processing
        ;;
    esac
done

# Set default for --progress if it was not provided
if [ -z "$progress" ]; then
    progress="plain"
fi

# List of required binaries
required_binaries=("docker" "git" "grep")

# Loop through each binary and check if it's installed
for binary in "${required_binaries[@]}"; do
    if ! which "$binary" > /dev/null 2>&1; then
        echo "$binary is not installed. Please install $binary and try again."
        exit 1
    fi
done

echo "All required binaries are installed."

# Fetch the version number from pyproject.toml using bash and standard libraries/binaries only
version=$(grep -oP '(?<=^version = ")[^"]+(?=")' pyproject.toml)

echo "Version number fetched from pyproject.toml: $version"

# Check that all commits have been pushed to git
if [ $dry_run -eq 0 ]; then
    if [ $skip_git_check -eq 1 ]; then
        echo "Skipping git commit check as per --skip-git-check flag."
    else
      if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then
          echo "Not on main branch. Aborting."
          exit 1
      fi

      if [ "$(git rev-list origin/main..HEAD)" != "" ]; then
          echo "Not all commits have been pushed to git. Aborting."
          exit 1
      fi

      echo "Working on the main branch and all commits have been pushed to git."
    fi
fi

# Get the git commit's short-name
commit=$(git rev-parse --short HEAD)

echo "Git commit's short name: $commit"

name_version_commit="$image_name:$version-$commit"
name_version="$image_name:$version"

# Build the docker container with --no-persistent_silo
docker build --no-cache --progress $progress -t "$name_version_commit" .

# Check the exit status of the tests
if [ $? -ne 0 ]; then
    echo "Build failed. Aborting."
    exit 1
fi

echo "Built docker container with tag: $name_version_commit"

# Check the value of dry_run
if [ $dry_run -eq 0 ]; then
    # Push the image to docker_namespace/image_name

    # First push the version tags
    docker tag "$name_version_commit" "$name_version"
    docker push "$name_version"

    # Then push the version-commit tag
    docker tag "$name_version_commit" "$name_version_commit"
    docker push "$name_version_commit"

    echo "Pushed $name_version_commit"

    if [ "$skip_git_check" -eq 1 ]; then
        echo "Skipping tagging as latest due to --skip-git-check flag."
        exit 0

    else
      # Tag the newly uploaded image as latest
      docker tag "$name_version_commit" "$image_name:latest"
      docker push "$image_name:latest"

      echo "Pushed $name_version_commit and tagged as latest"
      exit 0
    fi

else
    echo "Dry run completed successfully. No changes were pushed."
    exit 0
fi
