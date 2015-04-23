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
    formset = ConsumableFormSet(initial=init, data=data)
    for form in formset:
        id = int(form["resource_id"].value())
        resource = EconomicResource.objects.get(id=id)
        form.identifier = resource.identifier
    return formset 

@login_required
def log_equipment_use(request, equip_resource_id, equip_use_rt_id, tech_rt_id, agent_id, pattern_id, consumable_rt_id, payment_rt_id):
    #import pdb; pdb.set_trace()
    equipment = get_object_or_404(EconomicResource, id=equip_resource_id)
    equipment_use_rt = get_object_or_404(EconomicResourceType, id=equip_use_rt_id)
    technician_rt = EconomicResourceType.objects.get(id=tech_rt_id)
    context_agent = get_object_or_404(EconomicAgent, id=agent_id)
    pattern = ProcessPattern.objects.get(id=pattern_id)
    consumable_rt = EconomicResourceType.objects.get(id=consumable_rt_id)
    agent = get_agent(request)
    init = {"event_date": datetime.date.today(), "from_agent": agent}
    equip_form = EquipmentUseForm(equip_resource=equipment, context_agent=context_agent, initial=init, data=request.POST or None)
    formset = consumable_formset(consumable_rt=consumable_rt)
    
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        if equip_form.is_valid():
            data = equip_form.cleaned_data
            input_date = data["event_date"]
            who = data["from_agent"]
            quantity = data["quantity"]
            technician = data["technician"]
            technician_quantity = data["technician_hours"]
            et_ship = EventType.objects.get(name="Shipment")
            sale = Exchange(
                name="Use of " + equipment.identifier,
                use_case=UseCase.objects.get(identifier="sale"),
                start_date=input_date,
                process_pattern=pattern,
                customer=who,
                created_by=request.user,
                context_agent=context_agent,
            )
            sale.save()
            usage_ship_event = EconomicEvent(
                event_type = et_ship,
                event_date = input_date,
                resource_type = equipment_use_rt,
                exchange = sale,
                from_agent = context_agent,
                to_agent = who,
                context_agent = context_agent,
                quantity = quantity,
                unit_of_quantity = equipment_use_rt.unit,
                value = quantity * equipment_use_rt.price_per_unit,
                unit_of_value = equipment_use_rt.unit_of_price,
                created_by = request.user,
            )
            usage_ship_event.save()
            if technician and technician_quantity > 0:
                tech_sale = Exchange(
                    name="Technician on " + equipment.identifier,
                    use_case=UseCase.objects.get(identifier="sale"),
                    start_date=input_date,
                    process_pattern=pattern,
                    customer=who,
                    created_by=request.user,
                    context_agent=context_agent,
                )
                tech_sale.save()
                tech_ship_event = EconomicEvent(
                    event_type = et_ship,
                    event_date = input_date,
                    resource_type = technician_rt,
                    exchange = tech_sale,
                    from_agent = technician,
                    to_agent = who,
                    context_agent = context_agent,
                    quantity = technician_quantity,
                    unit_of_quantity = technician_rt.unit,
                    value = technician_quantity * technician_rt.price_per_unit,
                    unit_of_value = technician_rt.unit_of_price,
                    created_by = request.user,
                )
                tech_ship_event.save()
            else:
                tech_sale = None
            #import pdb; pdb.set_trace()
            formset = consumable_formset(data=request.POST, consumable_rt=consumable_rt)
            for form in formset.forms:
                if form.is_valid():
                    data_cons = form.cleaned_data
                    if data_cons:
                        qty = data_cons["quantity"]
                        if qty:
                            if qty > 0:
                                res_id = data_cons["resource_id"]
                                consumable = EconomicResource.objects.get(id=int(res_id))
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
                                    value = quantity * consumable.value_per_unit_of_use,
                                    unit_of_value = consumable.resource_type.unit_of_price,
                                    created_by = request.user,
                                )
                                consume_ship_event.save()
        if tech_sale:
            return HttpResponseRedirect('/%s/%s/%s/%s/%s/'
                % ('equipment/pay-equipment-use', sale.id, payment_rt_id, equip_resource_id, tech_sale.id))
        else:
            return HttpResponseRedirect('/%s/%s/%s/%s/'
                % ('equipment/pay-equipment-use', sale.id, payment_rt_id, equip_resource_id))
    
    return render_to_response("equipment/log_equipment_use.html", {
        "equip_form": equip_form,
        "formset": formset,
        "equipment": equipment,
        "consumable_rt": consumable_rt,
    }, context_instance=RequestContext(request))

@login_required
def pay_equipment_use(request, sale_id, payment_rt_id, equip_resource_id, tech_sale_id=None):
    #import pdb; pdb.set_trace()
    sale = get_object_or_404(Exchange, id=sale_id)
    tech_sale = None
    if tech_sale_id:
        tech_sale = get_object_or_404(Exchange, id=tech_sale_id)
    payment_rt = EconomicResourceType.objects.get(id=payment_rt_id)
    payment_unit = payment_rt.unit
    equipment = EconomicResource.objects.get(id=equip_resource_id)
    paid = False
    tech_total = Decimal(0)
    sale_total = Decimal(0)
    tech_total_formatted = None
    ship_events = sale.shipment_events()
    for se in ship_events:
        sale_total += se.value
    sale_total_formatted = "".join([payment_rt.unit.symbol, str(sale_total.quantize(Decimal('.01'), rounding=ROUND_UP))])
    if tech_sale_id:
        tech_events = tech_sale.shipment_events()
        for te in tech_events:
            tech_total += te.value
            technician = te.from_agent
        tech_total_formatted = "".join([payment_rt.unit.symbol, str(tech_total.quantize(Decimal('.01'), rounding=ROUND_UP))])    
    
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        cr_et = EventType.objects.get(name="Cash Receipt")
        cr_event = EconomicEvent(
            event_type = cr_et,
            event_date = sale.start_date,
            exchange = sale,
            resource_type = payment_rt,
            from_agent = sale.customer,
            to_agent = sale.context_agent,
            context_agent = sale.context_agent,
            quantity = sale_total,
            unit_of_quantity = payment_unit,
            value = sale_total,
            unit_of_value = payment_unit,
            created_by = request.user,
        )
        cr_event.save()
        if tech_total > 0:
            tech_event = EconomicEvent(
                event_type = cr_et,
                event_date = tech_sale.start_date,
                exchange = tech_sale,
                resource_type = payment_rt,
                from_agent = tech_sale.customer,
                to_agent = technician,
                context_agent = sale.context_agent,
                quantity = tech_total,
                unit_of_quantity = payment_unit,
                value = tech_total,
                unit_of_value = payment_unit,
                created_by = request.user,
            )
            tech_event.save()
        paid = True
        
    return render_to_response("equipment/pay_equipment_use.html", {
        "sale": sale,
        "tech_sale": tech_sale,
        "sale_total": sale_total_formatted,
        "tech_total": tech_total_formatted,
        "payment_unit": payment_unit,
        "paid": paid,
        "equipment": equipment,
    }, context_instance=RequestContext(request))