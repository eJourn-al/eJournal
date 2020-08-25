#!/bin/bash

# Switch to postgres user before runnig this script.
# Was unsuccessfully integrated in the MakeFile because of the difficulties running a loop for a different user

dbPattern="test_ejournal%" # Matches anything starting with test_ejournal
sql="select datname from pg_database where datname like '${dbPattern}'"
dbDelNames=`psql -U postgres -t -A -c "$sql"`
for dbName in ${dbDelNames[@]}
do
    echo -e "[INFO] Drop $dbName.\n"
    psql -U postgres -c "DROP DATABASE IF EXISTS ${dbName};"
done
