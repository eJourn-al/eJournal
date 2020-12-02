SHELL := /bin/bash

ifdef test
TOTEST=-k ${test}
else
TOTEST=
endif

ifdef no_become
become =
else
become = --ask-become-pass
endif

ifndef branch
branch=`git rev-parse --abbrev-ref HEAD`
endif
ifndef host
host=staging
endif

ansible_play_default_flags = --ask-pass --ask-vault-pass

vars = --extra-vars "git_branch=${branch} deploy_host=${host}"

postgres_db = ejournal
postgres_test_db = test_$(postgres_db)
postgres_dev_user = ejournal
postgres_dev_user_pass = password

venv_activate = source ./venv/bin/activate

##### TEST COMMANDS #####

test-back:
	${venv_activate} \
	&& flake8 ./src/django \
	&& ./src/django/manage.py check --fail-level=WARNING \
	&& pytest ${TOTEST} src/django/test/
	make isort

test-front:
	${venv_activate} && npm run lint --prefix ./src/vue

display-coverage-plain:
	${venv_activate} && coverage report -m

display-coverage-html:
	${venv_activate} && coverage html

test: test-front test-back

run-test:
	${venv_activate} && cd ./src/django && python manage.py test test.test_$(arg)"

##### DEVELOP COMMANDS #####

run-front:
	${venv_activate} && npm run serve --prefix ./src/vue

run-back: isort
	${venv_activate} && python ./src/django/manage.py runserver

isort:
	${venv_activate} && isort -rc src/django/

setup:
	@echo "This operation will clean old files, press enter to continue (ctrl+c to cancel)"
	@read -r a
	make setup-no-input
	make setup-sentry-cli
	make run-preset-db
setup-no-input:
	@make clean

	make setup-git

	# Install apt dependencies and ppa's.
	(sudo apt-cache show python3.6 | grep "Package: python3.6") || \
	(sudo add-apt-repository ppa:deadsnakes/ppa -y; sudo apt update) || echo "0"

	sudo apt install npm -y
	sudo npm install npm@latest -g
	sudo apt install nodejs python3 python3-pip libpq-dev python3-dev postgresql postgresql-contrib rabbitmq-server python3-setuptools sshpass -y

	make setup-venv requirements_file=local.txt

	# Istall nodejs dependencies.
	npm install --prefix ./src/vue

	make postgres-init
	make migrate-back
	${venv_activate} && cd ./src/django && python manage.py migrate django_celery_results

	@echo "DONE!"

setup-ci:
	git submodule update --remote --merge
	sudo pip3 install virtualenv
	virtualenv -p python3 venv

	# Istall python dependencies.
	${venv_activate} && pip install -r requirements/ci.txt

	# Istall nodejs dependencies.
	npm install --prefix ./src/vue

	@echo "DONE!"

setup-venv:
	sudo pip3 install virtualenv
	virtualenv -p python3 venv

	${venv_activate} \
	&& pip install -r requirements/$(requirements_file) --use-feature=2020-resolver \
	&& ansible-playbook ./config/provision-local.yml --ask-vault-pass

setup-sentry-cli:
	@if ! [ $(shell which 'sentry-cli' > /dev/null 2>&1; echo $$?) -eq 0 ]; then \
		${venv_activate} && curl -sL https://sentry.io/get-cli/ | bash; \
	fi

setup-git:
	make git-update-submodules
	make git-set-custom-hooks-path

git-set-custom-hooks-path:
	git config core.hooksPath .githooks

git-update-submodules:
	git submodule update --remote --merge

output-webpack-config:
	${venv_activate} && cd ./src/vue && vue inspect > webpack_config_output.js

output-vue-build-report:
	${venv_activate} && npm run build-report --prefix ./src/vue

##### DEPLOY COMMANDS ######

ansible-test-connection:
	${venv_activate} &&	ansible -m ping all ${become}

run-ansible-provision:
	${venv_activate} && ansible-playbook config/provision-servers.yml ${ansible_play_default_flags} ${become} ${vars}

run-ansible-deploy:
	${venv_activate} && ansible-playbook config/provision-servers.yml ${ansible_play_default_flags} ${become} ${vars} --tags "deploy_front,deploy_back"

run-ansible-deploy-front:
	${venv_activate} && ansible-playbook config/provision-servers.yml ${ansible_play_default_flags} ${become} ${vars} --tags "deploy_front"

run-ansible-deploy-back:
	${venv_activate} && ansible-playbook config/provision-servers.yml ${ansible_play_default_flags} ${become} ${vars} --tags "deploy_back"

run-ansible-backup:
	${venv_activate} && ansible-playbook config/provision-servers.yml ${ansible_play_default_flags} ${become} ${vars} --tags "backup"

run-ansible-preset_db:
	${venv_activate} && ansible-playbook config/provision-servers.yml ${ansible_play_default_flags} ${become} ${vars} --tags "run_preset_db"

run-ansible-restore-latest:
	${venv_activate} && ansible-playbook config/provision-servers.yml ${ansible_play_default_flags} ${become} ${vars} --tags "restore_latest"

run-ansible-release:
	${venv_activate} && ansible-playbook config/release-local.yml ${ansible_play_default_flags} ${become} ${vars}

##### MAKEFILE COMMANDS #####

default:
	make setup-no-input
	make test

clean:
	rm -rf ./venv
	rm -rf ./src/vue/node_modules
	@if [ $(shell id "postgres" > /dev/null 2>&1; echo $$?) -eq 0 ]; then \
		make postgres-clean; \
	fi

##### DATABSE COMMANDS #####

postgres-clean:
	@sudo su -c "psql \
	-c \"DROP DATABASE IF EXISTS $(postgres_db)\" \
	-c \"DROP DATABASE IF EXISTS test_$(postgres_db)\" \
	-c \"DROP USER IF EXISTS $(postgres_dev_user)\" \
	" postgres

postgres-init:
	@sudo su -c "psql \
	-c \"CREATE DATABASE $(postgres_db)\" \
	-c \"CREATE USER $(postgres_dev_user) WITH PASSWORD '$(postgres_dev_user_pass)'\" \
	-c \"ALTER ROLE $(postgres_dev_user) CREATEDB\" \
	-c \"ALTER ROLE $(postgres_dev_user) SET client_encoding TO 'utf8'\" \
	-c \"ALTER ROLE $(postgres_dev_user) SET default_transaction_isolation TO 'read committed'\" \
	-c \"ALTER ROLE $(postgres_dev_user) SET timezone TO 'CET'\" \
	-c \"GRANT ALL PRIVILEGES ON DATABASE $(postgres_db) TO $(postgres_dev_user)\" \
	-c \"alter role $(postgres_dev_user) superuser\" \
	" postgres

postgres-reset:
	make postgres-clean
	make postgres-init

preset-db:
	@echo "This operation will wipe the $(postgres_db) database, press enter to continue (ctrl+c to cancel)"
	@read -r a
	make preset-db-no-input
preset-db-no-input:
	rm -rf src/django/media/*
	make postgres-reset
	make migrate-back
	make run-preset-db

run-preset-db:
	${venv_activate} && cd ./src/django && python manage.py preset_db $(n_performance_students)

run-add-performance-course:
	${venv_activate} && cd ./src/django && python manage.py add_performance_course $(n_performance_students)

migrate-back:
	${venv_activate} && cd ./src/django && python manage.py makemigrations VLE && python manage.py migrate

migrate-merge:
	${venv_activate} && cd ./src/django && python manage.py makemigrations --merge

db-dump:
	@pg_dump --dbname=postgresql://$(postgres_dev_user):$(postgres_dev_user_pass)@127.0.0.1:5432/$(dbname) > db.dump
	@echo dump to file: db.dump success!

db-restore:
	@echo "This operation will wipe and then restore the $(postgres_db) database from db.dump, press enter to continue (ctrl+c to cancel)"
	@read -r a
	@sudo su -c "psql \
	-c \"DROP DATABASE IF EXISTS $(postgres_db)\" \
	-c \"DROP DATABASE IF EXISTS test_$(postgres_db)\" \
	-c \"CREATE DATABASE $(postgres_db)\" \
	" postgres
	@psql --dbname=postgresql://$(postgres_dev_user):$(postgres_dev_user_pass)@127.0.0.1:5432/$(dbname) < db.dump

##### MISC COMMANDS #####

superuser:
	${venv_activate} && python src/django/manage.py createsuperuser

update-dependencies:
	npm update --dev --prefix ./src/vue
	npm install --prefix ./src/vue

fix-npm:
	npm cache clean -f
	npm config set strict-ssl false
	sudo npm install -g n
	npm config set strict-ssl true
	sudo n stable

fix-live-reload:
	echo $$(( `sudo cat /proc/sys/fs/inotify/max_user_watches` * 2 )) | sudo tee /proc/sys/fs/inotify/max_user_watches

shell:
	${venv_activate} \
	&& export PYTHONSTARTUP="./shell_startup.py" \
	&& cd ./src/django \
	&& python manage.py shell

run-celery-worker-and-beat:
	sudo rabbitmqctl purge_queue celery && ${venv_activate} && cd ./src/django && celery -A VLE worker -l info -B

encrypt_vault_var:
	${venv_activate} && ansible-vault encrypt_string "${inp}" --vault-password-file ./pass.txt
