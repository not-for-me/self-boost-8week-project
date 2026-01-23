#!/bin/bash
# Label Studio 중지 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$WORKSPACE_DIR"

echo "Stopping Label Studio..."
docker compose down

echo "Label Studio stopped."
