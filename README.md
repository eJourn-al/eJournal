<p align="center">
    <img width="250" src="https://avatars1.githubusercontent.com/u/41028230"/>
</p>  

[![Build Status](https://travis-ci.com/eJourn-al/eJournal.svg?branch=develop)](https://travis-ci.com/eJourn-al/eJournal) [![Coverage Status](https://codecov.io/gh/eJourn-al/eJournal/branch/develop/graph/badge.svg)](https://codecov.io/gh/eJourn-al/eJournal)

eJournal is a platform for online journalling and long term assignments, especially developed for education. It can be easily connected to virtual learning environments through LTI.

## Contributing

For information about contributing to the project, see [CONTRIBUTING.MD](CONTRIBUTING.MD).

## Deployment

### Preconfiguring Production

In the file `settings/deploy.conf` there are multiple options to configure:

- `APACHE_DIR`: should be pointed to the directory where apache is installed (defaults to `/etc/apache2`).
- `TARGET`: should be the directory where apache will be serving files from (defaults to `/var/www/ejournal`).
- `TYPE`: should be the http type: either http or https (defaults to `http`).
- `SERVERNAME`: should be the website URL. The site will be accessible on `$URL:$PORT$HOOKPOINT` (defaults to `localhost`).
- `APIURL`: should be the API URL. The API will be accessible on `$APIURL:$PORT$HOOKPOINT` (defaults to `api.localhost`).
- `PORT`: should be the port the website will be accessible over, this will be appended to the `$APACHE_DIR/ports.conf` file (defaults to `80`).
- `HOOKPOINT`: Defines the path after the URL to serve as a root folder for this project. Should always end with a `/` (defaults to `/`).


In the file `settings/database.conf` you will need to configure the database. By default we use [postgresql](https://www.postgresql.org/).

- `DATABASE_TYPE`: the backend of the database. Can be one of the backends [specified by django](https://docs.djangoproject.com/en/2.0/ref/settings/#std:setting-DATABASE-ENGINE) (defaults to postgresql).
- `DATABASE_NAME`: the name of the database (defaults to ejournal).
- `DATABASE_HOST`: the URL of the server running the database (defaults to localhost).
- `DATABASE_PORT`: the port on which the database is accessible through `$DATABASE_HOST` (default PostgreSQL port is 5432).
- `DATABASE_USER`: the user for the server to create as database owner. Note that this user will gain all rights for the table set in `$DATABASE_NAME`, as this is required for the server to be able to freely manipulate the database.
- `DATABASE_PASSWORD`: the password that is set for the `$DATABASE_USER`.

In the file `settings/secrets.conf` you will be required to generate new secret keys for django and LTI. Neither of these fields should be the same, and it is suggested you use a random string generator to generate the secret.
Use a sufficiently long and complex secret (the default by django is 50 characters).

### Installing

```bash
make install
```

This will, if not already installed, install [apache2](https://httpd.apache.org/), apache2-dev, and [wsgi_mod 4.6.4](https://github.com/GrahamDumpleton/mod_wsgi) from source.
It sets up the modular `wsgi.conf` file in `$APACHE_DIR/conf-available/` and automatically enables it.
It also sets up the modular `ejournal.conf` file in `$APACHE_DIR/sites-available/` and enables it on the set port (default 8080), also adding the port to the `$APACHE_DIR/ports.conf` file.

This only needs to be run once, as initial deployment setup.

### Deploying

To update the server with your cloned version of eJournal, you will have to run:

```bash
make deploy
```

This compiles and copies the source files and static files to the destination folder, replacing configurables where needed.

#### Serving

To simplify restarting the server, the following command restarts the apache server to handle any updated files:

```bash
make serve
```

### Additional Configuration

#### Create a Superuser

If this is the first time deploying the code to a server instance, you may want to make a superuser. A superuser will be an user that can access /admin and therefore set up the site according to their will. At least one superuser is required, else no initial courses, assignments and journals can be created.

A superuser is created by running the following commands while in the `$TARGET` folder:

```bash
source ./venv/bin/activate
python ./django/manage.py createsuperuser
deactivate
```

Make sure to use a strong password, as these credentials will be able to manipulate the database at will.

## Troubleshooting

The setup and deployment scripts have been built for ubuntu, and may not work on any other linux distributions. May the need for this arise, the scripts can be altered to support additional distributions. 
May the setup or deployment fail, feel free to contact us at support@ejournal.app.

## Contributors

Jeroen van Bennekum,
Xavier van Dommelen,
Okke van Eck,
Engel Hamer,
Lars van Hijfte,
Hendrik Huang,
Maarten van Keulen,
Joey Lai,
Teun Mathijssen,
Rick Watertor,
Dennis Wind,
Zi Long Zhu.
