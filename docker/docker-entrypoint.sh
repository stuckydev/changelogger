#!/bin/sh
set -eu

mkdir -p /app/data
echo "changelogger: starting"

exec "$@"
