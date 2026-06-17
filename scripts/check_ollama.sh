#!/usr/bin/env bash
# check_ollama.sh
# 로컬 개발 환경에서 Ollama 서비스의 구동 여부 및 qwen2.5:14b-instruct-q4_K_M 모델 존재 여부를 검증합니다.

OLLAMA_API="http://localhost:11434"
MODEL_NAME="qwen2.5:14b-instruct-q4_K_M"

echo "Checking Ollama status at $OLLAMA_API..."

# curl을 통해 api/tags 호출
response=$(curl -s -m 5 "$OLLAMA_API/api/tags")

if [ $? -ne 0 ]; then
  echo "Error: Failed to connect to Ollama service. Ensure Ollama is running locally."
  echo "Download and install from: https://ollama.com"
  exit 1
fi

# jq가 설치되어 있는 경우 파싱 점검, 미설치 시 grep으로 단순 존재 여부 점검
if command -v jq &> /dev/null; then
  models=$(echo "$response" | jq -r '.models[].name')
  found=false
  for m in $models; do
    if [[ "$m" == "$MODEL_NAME" || "$m" == "$MODEL_NAME"* ]]; then
      found=true
      break
    fi
  done
else
  # jq 미설치 환경 대응 fallback grep
  if echo "$response" | grep -q "$MODEL_NAME"; then
    found=true
  fi
fi

if [ "$found" = true ]; then
  echo "[OK] Ollama is running and model '$MODEL_NAME' is installed."
  exit 0
else
  echo "Warning: Ollama is running, but model '$MODEL_NAME' was not found."
  echo "Please pull the model first by running:"
  echo "  ollama pull $MODEL_NAME"
  exit 1
fi
