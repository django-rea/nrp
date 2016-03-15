from django.conf.urls import patterns, url
from django.views.generic.simple import direct_to_template

urlpatterns = patterns("",
    url(r'^my-dashboard/$', 'work.views.my_dashboard', name="my_dashboard"),
    url(r'^work-timer/(?P<process_id>\d+)/(?P<commitment_id>\d+)/$', 'work.views.work_timer', name="work_timer"),
    url(r'^process-logging/(?P<process_id>\d+)/$', 'work.views.process_logging', name="process_logging"),
    url(r'^work-process-finished/(?P<process_id>\d+)/$', 'work.views.work_process_finished', name="work_process_finished"),
    url(r'^my-history/$', 'work.views.my_history', name="my_history"),
    url(r'^register-skills/$', 'work.views.register_skills', name="register_skills"),
    url(r'^work-home/$', 'work.views.work_home', name="work_home"),
    url(r'^map/$', 'work.views.map', name="map"),
)