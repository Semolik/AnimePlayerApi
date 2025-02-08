#!/bin/bash
if [ -L "./db-data" ]; then
    alembic upgrade head
else
    alembic stamp head
fi
