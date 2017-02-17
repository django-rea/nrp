This is a howto for installing ocp in a RHEL/CentOS/Fedora system
=================================================================

- Install dependencies in the system: ::

    sudo yum groupinstall "Development Tools"
    sudo yum install python-devel python-setuptools python-virtualenv nano

- Clone repository and create virtual environment and install dependencies: ::

    cd /var/www
    git clone https://github.com/gopacifia/DEEP .
    cd DEEP
    virtualenv env
    source env/bin/activate
    pip install -r requirements.txt --trusted-host dist.pinaxproject.com
    deactivate

- Install uWSGI server (globally): ::

    easy_install pip
    pip install uwsgi
    # Hack below since libiconv is included by default in libc, but uwsgi complains otherwise
    cd /usr/lib64
    ln -s libc.so libiconv.so.2

- Time to check uWSGI greets you without any error: ::

    uwsgi

It should output something like below: ::

    *** Starting uWSGI 2.0.14 (64bit) on [...]
    [...]


PostgreSQL Configuration
========================

- Install PostgreSQL: ::

    yum install postgresql-server postgresql-contrib postgresql-devel
    postgresql-setup initdb
    nano /var/lib/pgsql/data/pg_hba.conf
    # In the file above replace ident with md5 so the lines are as follows:
        # IPv4 local connections:
        host    all             all             127.0.0.1/32            md5
        # IPv6 local connections:
        host    all             all             ::1/128                 md5

- Start and enable PostgreSQL at startup: ::

    systemctl start postgresql
    systemctl enable postgresql

- Create user and database (as root): ::

    su - postgres
    createuser -d -r -P nrp
    # Input "nrp" as password
    createdb -O nrp nrp

- Populate database, load some data, run tests and start with dev server: ::

    ./manage.py migrate auth
    ./manage.py migrate

Nginx and WSGI configuration
==============================

- Install system dependencies: ::

    sudo yum install nginx
    systemctl start nginx
    systemctl enable nginx

- Setup a secure website with certification. See:

    https://letsencrypt.org/
    https://certbot.eff.org/

- Configure virtual host: ::

    su
    cp /var/www/DEEP/docs/nginx_configuration/etc/nginx/conf.d/valuenetwork.conf /etc/nginx/conf.d/
    nano /etc/nginx/conf.d/valuenetwork.conf # Configure variables according to header in that file
    systemctl restart nginx

- Configure uWSGI service: ::

    su
    cp /var/www/DEEP/docs/nginx_configuration/etc/systemd/system/uwsgi.service /etc/systemd/system/uwsgi.service
    systemctl daemon-reload
    cp /var/www/DEEP/docs/nginx_configuration/var/www/DEEP/valuenetwork/local_settings.py /var/www/DEEP/valuenetwork/local_settings.py
    cp /var/www/DEEP/docs/nginx_configuration/var/www/DEEP/app.ini /var/www/DEEP/app.ini
    systemctl enable uwsgi

- Collect static resources: ::

    python manage.py collectstatic
    mv valuenetwork/site_media .

- Set up permissions and SELinux stuff: ::

    chown -R nginx:nginx /var/www/DEEP
    chcon -R -t httpd_sys_rw_content_t /var/www/DEEP

- Final steps: ::

    systemctl start uwsgi
    systemctl restart nginx
    cd /var/www/DEEP
    source env/bin/activate
    python manage.py createsuperuser # fill your user details to use later on

That's all!
