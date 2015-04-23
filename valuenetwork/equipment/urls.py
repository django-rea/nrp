from django.conf.urls import patterns, url
from django.views.generic.simple import direct_to_template

urlpatterns = patterns("",
    url(r"^log-equipment-use/(?P<equip_resource_id>\d+)/(?P<equip_use_rt_id>\d+)/(?P<tech_rt_id>\d+)/(?P<agent_id>\d+)/(?P<pattern_id>\d+)/(?P<consumable_rt_id>\d+)/(?P<payment_rt_id>\d+)/$",
        'valuenetwork.equipment.views.log_equipment_use', name="log_equipment_use"),
    url(r"^pay-equipment-use/(?P<sale_id>\d+)/(?P<payment_rt_id>\d+)/(?P<equip_resource_id>\d+)/(?P<tech_sale_id>\d+)/$", 'valuenetwork.equipment.views.pay_equipment_use',
        name="pay_equipment_use"),
    url(r"^pay-equipment-use/(?P<sale_id>\d+)/(?P<payment_rt_id>\d+)/(?P<equip_resource_id>\d+)/$", 'valuenetwork.equipment.views.pay_equipment_use',
        name="pay_equipment_use"),
)