#!/bin/bash
# Demo 5 - Infra healthcheck

docker compose up -d postgres redis
sleep 4
docker compose up -d --build gateway
sleep 5
curl -s http://localhost:8000/health
echo ""
echo "To stop: docker compose down"
