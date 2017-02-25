from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from django.conf.urls import url, include

from rest_framework import routers

from django_rea.api import views

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'people', views.PeopleViewSet, 'people')
router.register(r'contexts', views.ContextViewSet, 'context')
router.register(r'allagents', views.AgentViewSet, 'economicagent')
router.register(r'agent-types', views.AgentTypeViewSet)
router.register(r'economic-events', views.EconomicEventViewSet, 'economicevent')
router.register(r'contributions', views.ContributionViewSet, 'contribution')
router.register(r'event-types', views.EventTypeViewSet, 'eventtype')
router.register(r'resource-types', views.ResourceTypeViewSet, 'economicresourcetype')
router.register(r'resources', views.EconomicResourceViewSet, 'economicresource')
router.register(r'units', views.UnitViewSet)

router.register(r'usercreation', views.UserCreationViewSet, 'usercreation')
router.register(r'agentcreation', views.AgentCreationViewSet, 'agentcreation')
router.register(r'agentuser', views.AgentUserViewSet, 'agentuser')

urlpatterns = patterns("",
                       url(r'^', include(router.urls)),
                       url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
                       url(r"^agent-jsonld/$", 'django_rea.api.views.agent_jsonld', name="agent_jsonld"),
                       url(r"^agent-lod/(?P<agent_id>\d+)/$", 'django_rea.api.views.agent_lod', name="agent_lod"),
                       url(r"^agent-type-lod/(?P<agent_type_name>\w+)/$", 'django_rea.api.views.agent_type_lod', name="agent_type_lod"),
                       url(r"^agent-relationship-type-lod/(?P<agent_assoc_type_name>\w+)/$",
                           'django_rea.api.views.agent_relationship_type_lod', name="agent_relationship_type_lod"),
                       url(r"^agent-relationship-lod/(?P<agent_assoc_id>\d+)/$",
                           'django_rea.api.views.agent_relationship_lod', name="agent_relationship_lod"),
                       url(r"^agent-relationship-inv-lod/(?P<agent_assoc_id>\d+)/$",
                           'django_rea.api.views.agent_relationship_inv_lod', name="agent_relationship_inv_lod"),
                       url(r"^agent-jsonld-query/$", 'django_rea.api.views.agent_jsonld_query', name="agent_jsonld_query"),

                       )
