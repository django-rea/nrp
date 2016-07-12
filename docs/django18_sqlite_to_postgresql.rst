We have ocp running with django 1.8.13 and sqlite3. We want to migrate to postgeSQL database.

- install system dependencies: ::

    sudo apt-get install python-psycopg2 libpq-dev

- install psycopg2 in your virtualenv: ::

    cd valuenetwork
    source ../env/bin/activate
    pip install psycopg2

- Dump db: ::

    ./manage.py dumpdata --exclude contenttypes.contenttype --exclude sessions.session --exclude auth.permission --exclude account --exclude corsheaders.corsmodel --indent=4 > valnet.json

- Switch the backend in settings.py (or in local_settings.py): ::

    DATABASES = {
        "default": {
        # COMMENT OUT:
        #    "ENGINE": "django.db.backends.sqlite3",
        #    "NAME": "valuenetwork.sqlite",
        # ADD THIS INSTEAD:
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'db_name',                      
            'USER': 'db_user',
            'PASSWORD': 'db_user_password',
            'HOST': '',
            'PORT': 'db_port_number',
        }    
    }

- Create postgreSQL db: ::

    ./manage.py makemigrations
    ./manage.py makemigrations account
    ./manage.py migrate
 
- truncate some tables (delete all the data, but not the tables). From the db user do: ::

    psql
    TRUNCATE TABLE valueaccounting_agenttype, valueaccounting_agentassociationtype, valueaccounting_eventtype, valueaccounting_usecase, valueaccounting_usecaseeventtype CASCADE;

- Load data in the postgreSQL new db: ::

    ./manage.py loaddata valnet.json

- Migrate images of the users or delete the links with this, pasted into shell_plus: ::

    rts = EconomicResourceType.objects.all()
    for rt in rts:
        rt.photo=None
        rt.save()

::

    rs = EconomicResource.objects.all()
    for r in rs:
        r.photo=None
        r.save()

::

    agts = EconomicAgent.objects.all()
    for a in agts:
        a.photo=None
        a.save()

- That's all.

