#!/bin/bash
cd /opt/ha/config/custom_components/hanchu-ess-ha
git pull http://yuchengqian:password_1@git.guoxia.cloud/backend/ess/hanchu-ess-ha
sleep 2
docker restart homeassistant
