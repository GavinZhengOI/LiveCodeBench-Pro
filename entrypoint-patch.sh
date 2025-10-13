#!/usr/bin/env bash
set -euo pipefail
# 启动 go-judge（沙箱）
/usr/local/bin/go-judge -parallelism "${GJ_PARALLELISM}" -cpuset 1 &
sleep 0.5
# 启动 orchestrator
node /app/server.js
