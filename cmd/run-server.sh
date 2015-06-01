#!/bin/bash

cp /var/www/valuenetwork/valuenetwork/local_settings{_development,}.py
cd /var/www/valuenetwork && ./manage.py runserver