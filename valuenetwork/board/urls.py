from django.conf.urls import patterns, url
from django.views.generic.simple import direct_to_template

urlpatterns = patterns("",
    url(r'^dhen-board/(?P<context_agent_id>\d+)/$', 'valuenetwork.board.views.dhen_board', name="dhen_board"),
    url(r'^add-available/(?P<context_agent_id>\d+)/$', 'valuenetwork.board.views.add_available', name="add_available"),
)