from django.conf.urls import patterns, url
from django.views.generic.simple import direct_to_template

urlpatterns = patterns("",
    url(r"^log-equipment-use/(?P<scenario>\d+)/(?P<equip_resource_id>\d+)/(?P<context_agent_id>\d+)/(?P<pattern_id>\d+)/(?P<sale_pattern_id>\d+)/(?P<equip_svc_rt_id>\d+)/(?P<equip_fee_rt_id>\d+)/(?P<tech_rt_id>\d+)/(?P<consumable_rt_id>\d+)/(?P<payment_rt_id>\d+)/(?P<tech_rel_id>\d+)/(?P<ve_id>\d+)/(?P<va_id>\d+)/(?P<price_id>\d+)/(?P<part_rt_id>\d+)/(?P<cite_rt_id>\d+)/$",
        'valuenetwork.equipment.views.log_equipment_use', name="log_equipment_use"),
    url(r"^pay-equipment-use/(?P<scenario>\d+)/(?P<sale_id>\d+)/(?P<process_id>\d+)/(?P<payment_rt_id>\d+)/(?P<equip_resource_id>\d+)/(?P<mtnce_fee_event_id>\d+)/(?P<ve_id>\d+)/(?P<use_qty>\d+(\.\d*)?|\.\d+)/(?P<who_id>\d+)/$",
        'valuenetwork.equipment.views.pay_equipment_use', name="pay_equipment_use"),
    url(r"^pay-equipment-use/(?P<scenario>\d+)/(?P<sale_id>\d+)/(?P<process_id>\d+)/(?P<payment_rt_id>\d+)/(?P<equip_resource_id>\d+)/(?P<mtnce_fee_event_id>\d+)/(?P<ve_id>\d+)/(?P<use_qty>\d+(\.\d*)?|\.\d+)/(?P<who_id>\d+)/(?P<next_process_id>\d+)/(?P<cite_rt_id>\d+)/$",
        'valuenetwork.equipment.views.pay_equipment_use', name="pay_equipment_use"),
    url(r"^log-additional-inputs/(?P<cite_rt_id>\d+)/(?P<process_id>\d+)/$",
        'valuenetwork.equipment.views.log_additional_inputs', name="log_additional_inputs"),
)