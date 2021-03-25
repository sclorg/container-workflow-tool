#! /bin/bash

# Fail on error
set -ex

# Check vars needed by the image
[ -z "$WORKDIR" ] && echo 'ERROR: Please set the WORKDIR variable' && false
[ -z "$DOWNSTREAM_IMAGE_NAME" ] && echo 'ERROR: Please set the DOWNSTREAM_IMAGE_NAME variable' && false
[ -z "$UPSTREAM_IMAGE_NAME" ] && echo 'ERROR: Please set the UPSTREAM_IMAGE_NAME variable' && false

# Set vars used by CWT later
SOURCES="$WORKDIR"
RESULTS="$WORKDIR/results"
CWT_WD_PREFIX=${CWT_WD_PREFIX:-sync}
CWT_WD=/tmp/$CWT_WD_PREFIX
CWT_CONFIG_DIR=/tmp/container-workflow-tool/container_workflow_tool/config

# Get the OS info from source git
cd "$RESULTS"
config=$(git rev-parse --abbrev-ref HEAD)
echo "$config" | grep -q "main" && config="rawhide"

# Get the upstream folder name
cd "$CWT_DIR"
read -r _ ups_name _ <<<  "$(cwt --config "$CWT_CONFIG_DIR/$config.yaml" --do-image "$DOWNSTREAM_IMAGE_NAME" utils listupstream)"

# Copy sources to working directory for cwt to pick up
mkdir -p "$CWT_WD/upstreams/"
cp -r "$SOURCES/$UPSTREAM_IMAGE_NAME" "$CWT_WD/upstreams"
mv "$CWT_WD/upstreams/$UPSTREAM_IMAGE_NAME" "$CWT_WD/upstreams/$ups_name"
cp -r "$RESULTS" "$CWT_WD"
# Rename the dist-git folder to get the path expected by cwt
mv "$CWT_WD/results" "$CWT_WD/$DOWNSTREAM_IMAGE_NAME"
# Run cwt with internal configs against the working dir sources
cwt -v 5 --config "$CWT_CONFIG_DIR/$config.yaml" --disable-klist --base "$CWT_WD_PREFIX" --do-image "$DOWNSTREAM_IMAGE_NAME" git --commit-msg "" pullupstream

# Copy the results into the expected path
cp -r "$CWT_WD/$DOWNSTREAM_IMAGE_NAME"/* "$RESULTS"
