#!/bin/bash
# A script to sync the local project directory to the Raspberry Pi.

echo "Syncing files to the Raspberry Pi..."

rsync -avz --delete \
--exclude '.git' \
--exclude 'venv' \
--exclude '__pycache__' \
--exclude '.DS_Store' \
/Users/khrisendatpersaud/projects/toy_robot/ whoopsie@192.168.5.9:~/toy_robot

echo "Sync complete."
