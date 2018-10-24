#!/bin/bash

/usr/bin/supervisord --nodaemon --user root --configuration /etc/supervisor/supervisord.conf &

su - plu
