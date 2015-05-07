from django.conf.urls import patterns, url
from django.views.generic.simple import direct_to_template

urlpatterns = patterns("",
    url(r"^log-equipment-use/(?P<equip_resource_id>\d+)/(?P<context_agent_id>\d+)/(?P<pattern_id>\d+)/(?P<sale_pattern_id>\d+)/(?P<equip_svc_rt_id>\d+)/(?P<equip_fee_rt_id>\d+)/(?P<tech_rt_id>\d+)/(?P<consumable_rt_id>\d+)/(?P<payment_rt_id>\d+)/(?P<ve_id>\d+)/$",
        'valuenetwork.equipment.views.log_equipment_use', name="log_equipment_use"),
    url(r"^pay-equipment-use/(?P<sale_id>\d+)/(?P<process_id>\d+)/(?P<payment_rt_id>\d+)/(?P<equip_resource_id>\d+)/(?P<mtnce_fee_event_id>\d+)/$", 'valuenetwork.equipment.views.pay_equipment_use',
        name="pay_equipment_use"),
)