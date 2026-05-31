#!/bin/bash
# Bash Script to run PDF Extractor tests
set -e
echo -e "\033[36mRunning PDF Lossless Extraction Unit Tests...\033[0m"

# 루트 디렉토리에서 pytest 실행
uv run pytest backend/tests/unit/test_pdf_extractor.py -v
