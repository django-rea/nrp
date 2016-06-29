from django.conf.urls import patterns, url
from django.views.generic.simple import direct_to_template

urlpatterns = patterns("",
    url(r'^my-dashboard/$', 'work.views.my_dashboard', name="my_dashboard"),
    url(r'^non-process-logging/$', 'work.views.non_process_logging', name="non_process_logging"),
    url(r'^work-timer/(?P<process_id>\d+)/(?P<commitment_id>\d+)/$', 'work.views.work_timer', name="work_timer"),
    url(r'^process-logging/(?P<process_id>\d+)/$', 'work.views.process_logging', name="process_logging"),
    url(r'^work-process-finished/(?P<process_id>\d+)/$', 'work.views.work_process_finished', name="work_process_finished"),
    url(r'^my-history/$', 'work.views.my_history', name="my_history"),
    url(r'^work-home/$', 'work.views.work_home', name="work_home"),
    url(r'^save-timed-work-now/(?P<event_id>\d+)/$', 'work.views.save_timed_work_now', name="save_timed_work_now"),
    url(r'^change-history-event/(?P<event_id>\d+)/$', 'work.views.change_history_event', name="change_history_event"),
    url(r'^map/$', 'work.views.map', name="map"),
    url(r'^profile/$', 'work.views.profile', name="profile"),
    url(r'^change-personal-info/(?P<agent_id>\d+)/$', 'work.views.change_personal_info', name="change_personal_info"),
    url(r'^upload-picture/(?P<agent_id>\d+)/$', 'work.views.upload_picture', name="upload_picture"),
    url(r'^update-skills/(?P<agent_id>\d+)/$', 'work.views.update_skills', name="update_skills"),
    url(r"^add-worker-to-location/(?P<location_id>\d+)/(?P<agent_id>\d+)/$", 'work.views.add_worker_to_location', name="add_worker_to_location"),
    url(r"^add-location-to-worker/(?P<agent_id>\d+)/$", 'work.views.add_location_to_worker', name="add_location_to_worker"),
    url(r"^manage-faircoin-account/(?P<resource_id>\d+)/$", 'work.views.manage_faircoin_account', name="manage_faircoin_account"),
    url(r"^transfer-faircoins/(?P<resource_id>\d+)/$", 'work.views.transfer_faircoins', 
        name="transfer_faircoins"),
    url(r"^faircoin-history/(?P<resource_id>\d+)/$", 'work.views.faircoin_history', 
        name="faircoin_history"),
    url(r'^membership/$', 'work.views.membership_request', name="membership_request"),
    url(r'^membershipthanks/$', direct_to_template, {
        'template': 'work/membership_thanks.html'
    }, name="membership_thanks"),
)