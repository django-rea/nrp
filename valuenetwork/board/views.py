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
from valuenetwork.board.forms import *
from valuenetwork.valueaccounting.views import get_agent

#todo: a lot of this can be configured instead of hard-coded
def dhen_board(request, context_agent_id):
    #import pdb; pdb.set_trace()
    context_agent = get_object_or_404(EconomicAgent, id=context_agent_id)
    agent = get_agent(request)
    pattern = ProcessPattern.objects.get(name="Available")
    e_date = datetime.date.today()
    init = {"event_date": e_date,}
    available_form = AvailableForm(initial=init, pattern=pattern, context_agent=context_agent)
    process_form = PlanProcessForm()
    et = EventType.objects.get(name="Make Available") #todo: need more generic way to get all the rts to be tracked
    rts = pattern.get_resource_types(event_type=et)
    farm_stage = AgentAssociationType.objects.get(identifier="HarvestSite")
    for rt in rts:
        rt.farm_resources = rt.onhand_for_exchange_stage(stage=farm_stage)
        for res in rt.farm_resources:
            res.owns = res.available_events()[0].from_agent
            if res.available_events()[0].event_date > e_date:
                res.future = True
            prefix = res.form_prefix()
            qty_help = " ".join([res.unit_of_quantity().abbrev, ", up to 2 decimal places"])
            res.transfer_form = ExchangeFlowForm(initial=init, qty_help=qty_help, assoc_type_identifier="Harvester", context_agent=context_agent, prefix=prefix)
    
    return render_to_response("board/dhen_board.html", {
        "agent": agent,
        "context_agent": context_agent,
        "available_form": available_form,
        "process_form": process_form,
        "resource_types": rts,
    }, context_instance=RequestContext(request))

@login_required
def add_available(request, context_agent_id, assoc_type_identifier):
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        form = AvailableForm(data=request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.event_type = EventType.objects.get(name="Make Available")
            event.to_agent = event.from_agent
            event.context_agent = EconomicAgent.objects.get(id=context_agent_id)
            event.unit_of_quantity = event.resource_type.unit
            event.exchange_stage = AgentAssociationType.objects.get(identifier=assoc_type_identifier)
            event.created_by = request.user
            event.save()
            resource = EconomicResource(
                resource_type=event.resource_type,
                identifier="Farm-" + str(event.event_date),
                quantity=event.quantity,
                exchange_stage=AgentAssociationType.objects.get(identifier="HarvestSite"),
                current_location=event.from_agent.primary_location,
                created_by=request.user,                
            )
            resource.save()
            event.resource = resource
            event.save()
    return HttpResponseRedirect('/%s/%s/'
        % ('board/dhen-board', context_agent_id))

@login_required
def transfer_resource(request, context_agent_id, resource_id, assoc_type_identifier):
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        resource = EconomicResource.objects.get(id=resource_id)
        stage = AgentAssociationType.objects.get(identifier=assoc_type_identifier)
        #todo: hardcoded recipe and exchange 
        if assoc_type_identifier == "HarvestSite":
            next_stage = AgentAssociationType.objects.get(identifier="Harvester")
        elif assoc_type_identifier == "Harvester":
            next_stage = AgentAssociationType.objects.get(identifier="Drying Site")
        elif assoc_type_identifier == "DryingSite":
            next_stage = AgentAssociationType.objects.get(identifier="Seller")
        else:
            next_stage = None
        from_agent = resource.last_exchange_event().to_agent
        prefix = resource.form_prefix()
        form = ExchangeFlowForm(prefix=prefix, data=request.POST)
        if form.is_valid():
            data = form.cleaned_data
            event_date = data["event_date"] 
            to_agent = data["to_agent"]
            quantity = data["quantity"]
            value = data["value"]
            unit_of_value = data["unit_of_value"]
            paid = data["paid"]
            notes  = data["notes"]
            use_case = UseCase.objects.get(identifier="transfer")
            exchange = Exchange(
                name="Transfer " + resource.resource_type.name,
                use_case=use_case,
                process_pattern=use_case.process_patterns()[0],
                start_date=event_date,
                context_agent=context_agent,
                created_by=request.user,                
            )
            exchange.save()
            xfer_event = EconomicEvent(
                event_type = EventType.objects.get(name="Transfer"),
                event_date = event_date,
                resource = resource,
                resource_type = resource.resource_type,
                exchange = exchange,
                from_agent = from_agent,
                to_agent = to_agent,
                context_agent = context_agent,
                quantity = quantity,
                unit_of_quantity = resource.resource_type.unit,
                value = value,
                unit_of_value = unit_of_value,
                description = notes,
                created_by = request.user,
            )
            xfer_event.save()
            
            resource.quantity -= quantity
            if resource.quantity < 0:
                resource.quantity = 0
            resource.save()
            if paid == "paid":
                if value > 0:
                    rec_xfer_event = EconomicEvent(
                        event_type = EventType.objects.get(name="Reciprocal Transfer"),
                        event_date = event_date,
                        resource_type = ResourceType.objects.filter(unit__unit_type="value")[0],
                        exchange = exchange,
                        from_agent = from_agent,
                        to_agent = to_agent,
                        context_agent = context_agent,
                        quantity = quantity,
                        unit_of_quantity = resource.resource_type.unit,
                        value = value,
                        unit_of_value = unit_of_value,
                        description = notes,
                        created_by = request.user,                        
                    )
                    rec_xfer_event.save()
            elif paid == "later":
                if value > 0:
                    commit = Commitment (
                        
                    )
                    commit.save()
    return HttpResponseRedirect('/%s/%s/'
        % ('board/dhen-board', context_agent_id))
