#!/bin/sh

# this script is used to boot a Docker container
# upgrade the db, which currently happens in other admin functions
echo flask db upgrade...
while true; do
  flask db upgrade
  if [ $? -eq 0 ]; then
      break
  fi
  echo Deploy command failed, retrying in 5 secs...
  sleep 5
done

# Start the gunicorn server for api
echo starting gunicorn server...
exec gunicorn -b 0.0.0.0:$PORT --preload --timeout 200 --workers 4 --log-level=debug \
--access-logfile - --error-logfile - backend:app
