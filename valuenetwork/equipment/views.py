import datetime

from django.db.models import Q
from django.http import HttpResponse, HttpResponseServerError, Http404, HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.template import RequestContext
from django.core import serializers
from django.contrib.auth.decorators import login_required
from django.core.exceptions import MultipleObjectsReturned
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.forms.models import formset_factory, modelformset_factory, inlineformset_factory, BaseModelFormSet
from django.forms import ValidationError
from django.utils import simplejson
from django.utils.datastructures import SortedDict
from django.contrib.auth.forms import UserCreationForm
from django.conf import settings

from valuenetwork.valueaccounting.models import *
from valuenetwork.equipment.forms import *
from valuenetwork.valueaccounting.views import get_agent


def consumable_formset(consumable_rt, data=None):
    ConsumableFormSet = formset_factory(form=ConsumableForm, extra=0)
    init = []    
    consumable_resources = EconomicResource.objects.filter(resource_type=consumable_rt)
    for res in consumable_resources:
        d = {"resource_id": res.id,}
        init.append(d)   
    formset = ConsumableFormSet(initial=init)
    for form in formset:
        id = int(form["resource_id"].value())
        resource = EconomicResource.objects.get(id=id)
        form.identifier = resource.identifier
    return formset 

@login_required
def log_equipment_use(request, equip_use_resource_id, agent_id, pattern_id, consumable_rt_id):
    #import pdb; pdb.set_trace()
    equipment_use_resource = get_object_or_404(EconomicResource, id=equip_use_resource_id)
    context_agent = get_object_or_404(EconomicAgent, id=agent_id)
    pattern = ProcessPattern.objects.get(id=pattern_id)
    consumable_rt = EconomicResourceType.objects.get(id=consumable_rt_id)
    agent = get_agent(request)
    init = {"event_date": datetime.date.today(), "from_agent": agent}
    equip_form = EquipmentUseForm(resource=equipment_use_resource, context_agent=context_agent, initial=init, data=request.POST or None)
    formset = consumable_formset(consumable_rt=consumable_rt)
    
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        if equip_form.is_valid():
            ship_events = []
            data = equip_form.cleaned_data
            input_date = data["event_date"]
            who = data["from_agent"]
            quantity = data["quantity"]
            sale = Exchange(
                name="3D Printer Use",
                use_case=UseCase.objects.get(identifier="sale"),
                start_date=input_date,
                process_pattern=pattern,
                customer=who,
                created_by=request.user,
                context_agent=context_agent,
            )
            sale.save()
            usage_ship_event = EconomicEvent(
                event_type = EventType.objects.get(name="Shipment"),
                event_date = input_date,
                resource = equipment_use_resource,
                resource_type = equipment_use_resource.resource_type,
                exchange = sale,
                from_agent = context_agent,
                to_agent = who,
                context_agent = context_agent,
                quantity = quantity,
                unit_of_quantity = equipment_use_resource.resource_type.unit,
                value = quantity * equipment_use_resource.value_per_unit,
                unit_of_value = equipment_use_resource.resource_type.unit_of_value,
                created_by = request.user,
            )
            usage_ship_event.save()
            ship_events.append(usage_ship_event)
            import pdb; pdb.set_trace()
            formset = consumable_formset(data=request.POST, consumable_rt=consumable_rt)
            for form in formset:
                if form.is_valid():
                    data_cons = form.cleaned_data
                    if data_cons:
                        qty = data_cons["quantity"]
                        if qty:
                            if qty > 0:
                                res_id = data_cons["resource_id"]
                                consumable = EconomicResource.object.get(id=int(res_id))
                                consume_ship_event = EconomicEvent(
                                    event_type = EventType.objects.get(name="Shipment"),
                                    event_date = input_date,
                                    resource = consumable,
                                    resource_type = consumable.resource_type,
                                    exchange = sale,
                                    from_agent = context_agent,
                                    to_agent = who,
                                    context_agent = context_agent,
                                    quantity = qty,
                                    unit_of_quantity = consumable_rt.unit,
                                    created_by = request.user,
                                )
                                consume_ship_event.save()
                                ship_events.append(consume_ship_event)

    
    return render_to_response("equipment/log_equipment_use.html", {
        "equip_form": equip_form,
        "formset": formset,
        "equipment": equipment_use_resource,
        "consumable_rt": consumable_rt,
    }, context_instance=RequestContext(request))

