#!/bin/bash
cd /opt/ha/config/custom_components/hanchu-ess-ha
git pull http://yuchengqian:password_1@git.guoxia.cloud/backend/ess/hanchu-ess-ha
rm -rf __pycache__
sleep 2
docker restart homeassistant
