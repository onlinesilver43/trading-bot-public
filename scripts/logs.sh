#!/usr/bin/env bash
svc="${1:-tb-bot}"   # tb-bot or tb-ui
sshpass -f ~/.ssh/tb_pw ssh tb "docker logs -f $svc"
