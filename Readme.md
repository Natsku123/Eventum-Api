Eventum API
===========
### What is this?

Eventum API is an open-source [Flask](http://flask.pocoo.org/) based API project
and it works as a backend for [Eventum](https://github.com/Natsku123/Eventum).

### API Documentation


| URL | METHODS | EXPLANATION |PARAMETERS|
|-----|---------|-------------|----------|
|/|GET|Documentation #Todo|NO|
|/setup/|GET|Setup backend if not done|NO|
|/auth||Flask-JWT default authentication url|NO|
|/v1.0/users/|GET|Get all users|NO|
|/v1.0/users/create/|POST|Create user|NO|
|/v1.0/users/<user_id>/|GET|Get user|NO|
|/v1.0/users/<user_id>/update/|POST|Update password|NO|
|/v1.0/users/<user_id>/delete/|DELETE|Delete user|NO|
|/v1.0/events/|GET, POST|Interface for events|YES|
|/v1.0/events/newest/|GET|Newest event|NO|
|/v1.0/event/<event_id>/|GET|Get event|NO|
|/v1.0/event/<event_id>/edit/|POST|Edit event|NO|
|/v1.0/event/create/|POST|Create event|NO|
|/v1.0/event/<event_id>/participant/add/|POST|Add participant to event|NO|
|/v1.0/event/<event_id>/prices/|GET|Get prices for event|NO|
|/v1.0/event/<event_id>/role/<role_id>/price/|GET|Get price for event and role|NO|
|/v1.0/event/<event_id>/price/create/|POST|Create price for event|NO|
|/v1.0/event/<event_id>/role/<role_id>/price/edit/|POST|Edit price|NO|
|/v1.0/event/<event_id>/limits/|GET|Get limits for event|NO|
|/v1.0/event/<event_id>/role/<role_id>/limit/|GET|Get limit for event and role|NO|
|/v1.0/event/<event_id>/limit/create/|POST|Create event|NO|
|/v1.0/event/<event_id>/role/<role_id>/limit/edit/|POST|Edit limit|NO|
|/v1.0/humans/|GET|Interface for humans|YES|
|/v1.0/human/<human_id>/|GET|Get human|NO|
|/v1.0/human/<human_id>/events/|GET| Human's events|NO|
|/v1.0/participants/|GET, POST|Interface for participants|YES|
|/v1.0/participant/<participation_id>/payment/<status>|POST|Change participant payment status|NO|
|/v1.0/roles/|GET, POST|Interface for roles|YES|
|/v1.0/roles/create/|POST|Create role|NO|
|/v1.0/role/<role_id>/|GET|Get role|NO|
|/v1.0/role/<role_id>/edit/|POST|Edit role|NO|
|/v1.0/prices/|GET, POST|Interface for prices|YES|
|/v1.0/limits/|GET, POST|Interface for limits|YES|
|/v1.0/images/|GET, POST|Interface for images|YES|

#### Interfaces

[Eventum](https://github.com/Natsku123/Eventum) uses these by default.
Interfaces need parameters to function properly and they provide all
the same functions that other non-interface urls provide.

Note that /v1.0/users/ has no interface replacement!

#Todo write all parameters here


#### Authentication

See [Flask-JWT](https://pythonhosted.org/Flask-JWT/).


### Installation guide

#### Needed libraries

* PyMySQL
* Flask
* Flask-JWT
* Flask-CORS
* Werkzeug

#### Recommended Software

* [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/)
* [Nginx](https://www.nginx.com/)
* [MariaDB](https://mariadb.com/) (or other MySQL  database)
* [Certbot](https://certbot.eff.org/)
* [Python3.6>=](https://www.python.org)

If you want to use other software, feel free but I cannot provide an
installation guide for them at this time.

#### Installation

First, copy contents of this repository to
```bash
/var/www/eventum-api/
```
or path of your choice. But remember to replace it everywhere this was used! (configs and future steps)

Install software (run as root or sudo):
```bash
apt-get update
apt-get install mariadb-server
apt-get install nginx
apt-get install uwsgi
apt-get install certbot
```

Install libraries (make sure they end up as python3.6>= libraries):
```bash
pip install pymysql flask flask-jwt flask-cors
```

Open MariaDB:
```bash
mysql
```

If you set a password for root:
```bash
mysql -u root -p
```

Create database:
```mysql
CREATE DATABASE Eventum;
GRANT ALL PRIVILEGES ON Eventum.* TO 'eventum-user'@'localhost' IDENTIFIED BY 'nice password';
FLUSH PRIVILEGES;
```

In "config" folder there is a file called "config.template.json". Fill out all needed info and rename it to "config.json".
Be sure not to modify any keys!

Also fill out "uwsgi.template.ini" and save it as "uwsgi.ini".

Create uwsgi parameters (run with root or sudo):
```bash
nano /etc/nginx/uwsgi_params
```

And paste parameters from [this page](https://github.com/nginx/nginx/blob/master/conf/uwsgi_params) .

Create configuration for Nginx (run with root or sudo):
```bash
nano /etc/nginx/sites-available/eventum-api.conf
```

And fill it with this:
```bash
server {
    listen 80;
    server_name example.com www.example.com;
    root /var/www/eventum-api/;

    location / {
        include uwsgi_params;
        uwsgi_pass unix:/var/www/eventum-api/config/uwsgi.sock;
    }
}
```

Test that your configuration works (run with root or sudo):
```bash
nginx -t
```

If it works (run as root or sudo):
```bash
service nginx reload
```

Or:
```bash
service nginx restart
```

Now setup your domain to point to your servers IP-address.

And run certbot to give your site HTTPS (run as root or sudo):
```bash
certbot --nginx
```

Now you can run Eventum API with just
```bash
cd /var/www/eventum-api
uwsgi -ini config/uwsgi.ini
```

Or you could make systemd to run it...

First create new systemd configuration file (run as root or sudo):
```bash
nano /etc/systemd/system/eventum-api.uwsgi.service
```

And paste this into it:
```bash
[Unit]
Description=uWSGI Backend for Eventum
After=syslog.target

[Service]
WorkingDirectory=/var/www/eventum-api
ExecStart=/usr/local/bin/uwsgi --ini config/uwsgi.ini
# Requires systemd version 211 or newer
RuntimeDirectory=uwsgi
Restart=always
KillSignal=SIGQUIT
Type=notify
StandardError=syslog
NotifyAccess=all

[Install]
WantedBy=multi-user.target
```

Now run this to get your OS to recognize your new service (run as root or sudo):
```bash
systemctl daemon-reload
```

Start your Eventum API service to run it in the background (run as root or sudo)
```bash
service eventum-api.uwsgi start
```

If you get problems with permissions after this, run (as root or sudo):
```bash
chown [your-user-in-uwsgi.ini]:www-data /var/www/eventum-api/ -R
```

Next you probably should read [Eventum](https://github.com/Natsku123/Eventum)'s installation guide, if setting it up was the point.