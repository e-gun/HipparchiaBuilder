#!/usr/bin/env sh
# subprocess has troulbe calling pb_restore...
# pg_load --clean -U {user-name} -d {desintation_db} -f {dumpfilename.sql}
# export PGPASSWORD="HIPPAWRPASSHERE"

psql -d hipparchiaDB -f $1

