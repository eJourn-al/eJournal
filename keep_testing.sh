#!/bin/bash

if [[ -z ${1} ]]; then
    totest=
else
    totest="-k ${1}"
fi
sha=0
previous_sha=0
source ./venv/bin/activate


test () {
    stty size | perl -ale 'print "-"x$F[1]'
    stty size | perl -ale 'print "#"x$F[1]'
    stty size | perl -ale 'print "-"x$F[1]'
    pytest -c /dev/null src/django/test $totest && flake8 --max-line-length=120 src/django --exclude="src/django/VLE/migrations/*","src/django/VLE/settings/*","src/django/VLE/settings.py","src/django/VLE/tasks/__init__.py","./src/django/test/factory/__init__.py"
    isort -rc src/django/
    echo
    echo ">>> Press Enter to force update."
    previous_sha=`ls -lR src/django -I "media" | sha1sum`
}

while true; do
    sha=`ls -lR src/django -I "media" | sha1sum`
    if [[ $sha != $previous_sha ]] ; then
        test
    fi
    read -s -t 1 && test
done
