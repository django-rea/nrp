from django.conf.urls import patterns, url
from django.views.generic.simple import direct_to_template

urlpatterns = patterns("",
    url(r"^agent-jsonld/$", 'valuenetwork.api.views.agent_jsonld', name="agent_jsonld"),
    url(r"^agent-lod/(?P<agent_id>\d+)/$", 'valuenetwork.api.views.agent_lod', name="agent_lod"),
    url(r"^agent-type-lod/(?P<agent_type_name>\w+)/$", 'valuenetwork.api.views.agent_type_lod', name="agent_type_lod"),
    url(r"^agent-relationship-type-lod/(?P<agent_assoc_type_name>\w+)/$", 'valuenetwork.api.views.agent_relationship_type_lod', name="agent_relationship_type_lod"),
    url(r"^agent-relationship-lod/(?P<agent_assoc_id>\d+)/$", 'valuenetwork.api.views.agent_relationship_lod', name="agent_relationship_lod"),
    url(r"^agent-relationship-inv-lod/(?P<agent_assoc_id>\d+)/$", 'valuenetwork.api.views.agent_relationship_inv_lod', name="agent_relationship_inv_lod"),
    url(r"^agent-jsonld-query/$", 'valuenetwork.api.views.agent_jsonld_query', name="agent_jsonld_query"),
    
)