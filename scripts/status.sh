#!/usr/bin/env bash
sshpass -f ~/.ssh/tb_pw ssh tb '
set -e
docker compose -f /srv/trading-bots/compose/docker-compose.yml ps
'
