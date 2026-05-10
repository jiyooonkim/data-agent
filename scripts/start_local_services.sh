#!/bin/bash

# Local startup helper for the structured-data QA path.
# This script makes sure the local dependencies are ready:
# 1) Docker Desktop
# 2) docker compose services (PostgreSQL / Airflow)
# 3) Ollama server
# 4) qwen3:8b model for SQL generation

echo "== DATA-AGENT LOCAL STARTUP =="
echo ""
echo "1) Checking Docker Desktop ..."
docker ps >/dev/null 2>&1

if [ $? -ne 0 ]; then
  echo "Docker is not ready ... starting Docker Desktop !!"
  open -a Docker
  echo "Waiting a bit for Docker to wake up ..."
  sleep 15
else
  echo "Docker is already running !!"
fi

echo ""
echo "2) Starting project containers ..."
docker compose up -d

echo ""
echo "3) Checking Ollama server ..."
curl -s http://localhost:11434/api/tags >/dev/null 2>&1

if [ $? -ne 0 ]; then
  echo "Ollama is not ready ... starting local LLM server !!"
  nohup ollama serve >/tmp/data-agent-ollama.log 2>&1 &
  sleep 5
else
  echo "Ollama server is already running !!"
fi

echo ""
echo "4) Checking Qwen model ..."
ollama list | grep "qwen3:8b" >/dev/null 2>&1

if [ $? -ne 0 ]; then
  echo "Model qwen3:8b not found ... pulling now !!"
  ollama pull qwen3:8b
else
  echo "Model qwen3:8b is already installed !!"
fi

echo ""
echo "5) All set !!"
echo "You can now run this command ..."
echo "./.venv/bin/python main.py ask --question \"최근 7일 채널별 매출 합계 보여줘\""
