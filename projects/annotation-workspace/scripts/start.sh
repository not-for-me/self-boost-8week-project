#!/bin/bash
# Label Studio 시작 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$WORKSPACE_DIR"

# 데이터 디렉토리 생성
mkdir -p data/label-studio
mkdir -p data/local-files/images

echo "Starting Label Studio..."
docker compose up -d

echo ""
echo "Label Studio is starting at http://localhost:8080"
echo ""
echo "First-time setup:"
echo "  1. Open http://localhost:8080 in your browser"
echo "  2. Create an account (this is local, use any email)"
echo "  3. Create a new project"
echo "  4. In Settings > Labeling Interface, paste contents of:"
echo "     config/labeling-interface.xml"
echo ""
echo "To import images and predictions:"
echo "  1. Copy images to: data/local-files/images/"
echo "  2. Import predictions JSON via Label Studio UI"
echo ""
