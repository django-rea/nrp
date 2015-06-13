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
    available_form = AvailableForm(initial=init, pattern=pattern)
    process_form = PlanProcessForm()
    move_harvester_form = ExchangeFlowForm()
    move_dryer_form = ExchangeFlowForm()
    move_seller_form = ExchangeFlowForm()
    et = EventType.objects.get(name="Make Available") #todo: need more generic way to get all the rts to be tracked
    rts = pattern.get_resource_types(event_type=et)
    farm_stage = AgentAssociationType.objects.get(identifier="Grower")
    for rt in rts:
        rt.farm_resources = rt.onhand_for_exchange_stage(stage=farm_stage)
        for res in rt.farm_resources:
            res.owns = res.available_events()[0].from_agent
            if res.available_events()[0].event_date > e_date:
                res.future = True

    
    return render_to_response("board/dhen_board.html", {
        "agent": agent,
        "context_agent": context_agent,
        "available_form": available_form,
        "process_form": process_form,
        "move_harvester_form": move_harvester_form,
        "move_dryer_form": move_dryer_form,
        "move_seller_form": move_seller_form,
        "resource_types": rts,
    }, context_instance=RequestContext(request))

@login_required
def add_available(request, context_agent_id):
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        form = AvailableForm(data=request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.event_type = EventType.objects.get(name="Make Available")
            event.to_agent = event.from_agent
            event.context_agent = EconomicAgent.objects.get(id=context_agent_id)
            event.unit_of_quantity = event.resource_type.unit
            event.created_by = request.user
            event.save()
            resource = EconomicResource(
                resource_type=event.resource_type,
                identifier=str(event.event_date),
                quantity=event.quantity,
                exchange_stage=AgentAssociationType.objects.get(identifier="Grower"),
                current_location=event.from_agent.primary_location,
                created_by=request.user,                
            )
            resource.save()
            event.resource = resource
            event.save()
    return HttpResponseRedirect('/%s/%s/'
        % ('board/dhen-board', context_agent_id))