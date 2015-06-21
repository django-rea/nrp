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
    pattern = ProcessPattern.objects.get(name="Transfer")
    e_date = datetime.date.today()
    init = {"commitment_date": e_date, }
    available_form = AvailableForm(initial=init, pattern=pattern, context_agent=context_agent)
    process_form = PlanProcessForm()
    et = EventType.objects.get(name="Transfer")
    farm_stage = AgentAssociationType.objects.get(identifier="HarvestSite")
    #harvester_stage = AgentAssociationType.objects.get(identifier="Harvester")
    dryer_stage = AgentAssociationType.objects.get(identifier="DryingSite")
    seller_stage = AgentAssociationType.objects.get(identifier="Seller")
    rts = pattern.get_resource_types(event_type=et)
    for rt in rts:
        init = {"event_date": e_date, "paid": "paid"}
        rt.farm_commits = rt.commits_for_exchange_stage(stage=farm_stage) 
        for com in rt.farm_commits:
            if com.commitment_date > e_date:
                com.future = True
            prefix = com.form_prefix()
            qty_help = " ".join([com.unit_of_quantity.abbrev, ", up to 2 decimal places"])
            com.transfer_form = ExchangeFlowForm(initial=init, qty_help=qty_help, assoc_type_identifier="DryingSite", context_agent=context_agent, prefix=prefix)
            com.zero_form = ZeroOutForm(prefix=prefix)
            com.lot_form = NewResourceForm(prefix=prefix)
            com.multiple_formset = create_exchange_formset(context_agent=context_agent, assoc_type_identifier="Harvester", prefix=prefix)
        rt.dryer_resources = rt.onhand_for_exchange_stage(stage=dryer_stage)
        for res in rt.dryer_resources:
            res.owns = res.purchase_events()[0].from_agent
            prefix = res.form_prefix()
            qty_help = " ".join([res.unit_of_quantity().abbrev, ", up to 2 decimal places"])
            res.transfer_form = ExchangeFlowForm(initial=init, qty_help=qty_help, assoc_type_identifier="DryingSite", context_agent=context_agent, prefix=prefix)
          
    

    
    
    
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
        context_agent = EconomicAgent.objects.get(id=context_agent_id)
        form = AvailableForm(data=request.POST)
        if form.is_valid():
            commit = form.save(commit=False)
            commit.event_type = EventType.objects.get(name="Receipt")
            commit.to_agent = context_agent
            commit.context_agent = context_agent
            commit.due_date = commit.commitment_date
            commit.unit_of_quantity = commit.resource_type.unit
            commit.exchange_stage = AgentAssociationType.objects.get(identifier=assoc_type_identifier)
            commit.created_by = request.user
            commit.save()
    return HttpResponseRedirect('/%s/%s/'
        % ('board/dhen-board', context_agent_id))

def create_exchange_formset(context_agent, assoc_type_identifier, prefix, data=None):
    ExchangeFormSet = formset_factory(MultipleExchangeEventForm, extra=10)
    #init = {"paid": "paid"}
    formset = ExchangeFormSet(data=data, prefix=prefix)
    to_agents = context_agent.all_has_associates_by_type(assoc_type_identifier=assoc_type_identifier)
    for form in formset:
        #id = int(form["facet_id"].value())
        form.fields["to_agent"].queryset = to_agents
        form.fields["paid_stage_1"].initial = "paid"
        form.fields["paid_stage_2"].initial = "paid"
    return formset

@login_required
def purchase_resource(request, context_agent_id, assoc_type_identifier, commitment_id):
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        context_agent = EconomicAgent.objects.get(id=context_agent_id)
        stage = AgentAssociationType.objects.get(identifier=assoc_type_identifier)
        #todo: hardcoded recipe and exchange types
        if assoc_type_identifier == "HarvestSite":
            next_stage = AgentAssociationType.objects.get(identifier="Harvester")
        elif assoc_type_identifier == "Harvester":
            next_stage = AgentAssociationType.objects.get(identifier="DryingSite")
        elif assoc_type_identifier == "DryingSite":
            next_stage = AgentAssociationType.objects.get(identifier="Seller")
        else:
            next_stage = None
        
        commitment = Commitment.objects.get(id=commitment_id)
        prefix = commitment.form_prefix()
        form = ExchangeFlowForm(prefix=prefix, data=request.POST)
        lot_form = NewResourceForm(prefix=prefix, data=request.POST)
        zero_form = ZeroOutForm(prefix=prefix, data=request.POST)
        if form.is_valid() and lot_form.is_valid() and zero_form.is_valid():
            data = form.cleaned_data
            event_date = data["event_date"] 
            to_agent = data["to_agent"]
            #quantity = data["quantity"]
            #value = data["value"]
            #if not value:
            #    value = 0
            unit_of_value = data["unit_of_value"]
            #paid = data["paid"]
            notes  = data["notes"]
            lot_data = lot_form.cleaned_data
            identifier = lot_data["identifier"]
            zero_data = zero_form.cleaned_data
            zero_out = zero_data["zero_out"]
            bundle_stages = zero_data["bundle_stages"]
            purch_use_case = UseCase.objects.get(identifier="purch_contr")
            purch_pattern = None
            purch_patterns = [puc.pattern for puc in purch_use_case.patterns.all()]
            if purch_patterns:
                purch_pattern = purch_patterns[0]
            xfer_use_case = UseCase.objects.get(identifier="transfer")
            xfer_pattern = None
            xfer_patterns = [puc.pattern for puc in xfer_use_case.patterns.all()]
            if xfer_patterns:
                xfer_pattern = xfer_patterns[0]
            receipt_et = EventType.objects.get(name="Receipt")
            transfer_et = EventType.objects.get(name="Transfer")
            rec_transfer_et = EventType.objects.get(name="Reciprocal Transfer")
            pay_et = EventType.objects.get(name="Payment")
            consume_et = EventType.objects.get(name="Resource Consumption")
            produce_et = EventType.objects.get(name="Resource Production")
            pay_rt = EconomicResourceType.objects.filter(unit__unit_type="value")[0]
            formset = create_exchange_formset(prefix=prefix, data=request.POST, context_agent=context_agent, assoc_type_identifier=assoc_type_identifier)
            quantity = 0
            ces = []
            for form_ee in formset.forms:
                if form_ee.is_valid():
                    data_ee = form_ee.cleaned_data
                    breakout_to_agent = data_ee["to_agent"]
                    if breakout_to_agent:
                        breakout_quantity = data_ee["quantity"]
                        quantity += breakout_quantity
                        value_stage_1 = data_ee["value_stage_1"]
                        paid_stage_1 = data_ee["paid_stage_1"]
                        value_stage_2 = data_ee["value_stage_2"]
                        paid_stage_2 = data_ee["paid_stage_2"]
                        
                        exchange = Exchange(
                            name="Purchase " + commitment.resource_type.name,
                            use_case=purch_use_case,
                            process_pattern=purch_pattern,
                            start_date=event_date,
                            context_agent=context_agent,
                            created_by=request.user,                
                        )
                        exchange.save()
                        resource = EconomicResource(
                            identifier=commitment.resource_type.name + " from farm",
                            resource_type=commitment.resource_type,
                            quantity=breakout_quantity,
                            exchange_stage=next_stage,
                            created_by=request.user
                        )
                        resource.save()
                        receipt_event = EconomicEvent(
                            event_type = receipt_et,
                            event_date = event_date,
                            resource = resource,
                            resource_type = resource.resource_type,
                            exchange = exchange,
                            commitment=commitment,
                            from_agent = commitment.from_agent,
                            to_agent = breakout_to_agent,
                            context_agent = context_agent,
                            quantity = breakout_quantity,
                            unit_of_quantity = resource.resource_type.unit,
                            value = value_stage_1,
                            unit_of_value = unit_of_value,
                            created_by = request.user,
                        )
                        receipt_event.save()
                        if paid_stage_1 == "paid":
                            if value_stage_1 > 0:
                                pay_event_1 = EconomicEvent(
                                    event_type = pay_et,
                                    event_date = event_date,
                                    resource_type = pay_rt,
                                    exchange = exchange,
                                    exchange_stage=stage,
                                    from_agent = receipt_event.to_agent,
                                    to_agent = receipt_event.from_agent,
                                    context_agent = context_agent,
                                    quantity = value_stage_1,
                                    unit_of_quantity = unit_of_value,
                                    value = value_stage_1,
                                    unit_of_value = unit_of_value,
                                    created_by = request.user,                        
                                )
                                pay_event_1.save()
                        elif paid_stage_1 == "later":
                            if value_stage_1 > 0:
                                commit_1 = Commitment (
                                    commitment_date=event_date,
                                    event_type=pay_et,
                                    exchange=exchange,
                                    exchange_stage=stage,
                                    due_date=event_date,
                                    from_agent=receipt_event.to_agent,
                                    to_agent=receipt_event.from_agent,
                                    context_agent=context_agent,
                                    resource_type=pay_rt,
                                    quantity=value_stage_1,
                                    unit_of_quantity=unit_of_value,
                                    value=value_stage_1,
                                    unit_of_value=unit_of_value,
                                    created_by=request.user,                        
                                )
                                commit_1.save()
                                
                        xfer_exchange = Exchange(
                            name="Transfer " + commitment.resource_type.name,
                            use_case=xfer_use_case,
                            process_pattern=xfer_pattern,
                            start_date=event_date,
                            context_agent=context_agent,
                            created_by=request.user,                
                        )
                        xfer_exchange.save()
                        xfer_event = EconomicEvent(
                            event_type = transfer_et,
                            event_date = event_date,
                            resource = resource,
                            resource_type = resource.resource_type,
                            exchange = xfer_exchange,
                            from_agent = commitment.from_agent,
                            to_agent = breakout_to_agent,
                            context_agent = context_agent,
                            quantity = breakout_quantity,
                            unit_of_quantity = resource.resource_type.unit,
                            value = value_stage_1,
                            unit_of_value = unit_of_value,
                            created_by = request.user,
                        )
                        xfer_event.save()
                        if paid_stage_2 == "paid":
                            if value_stage_2 > 0:
                                pay_event_2 = EconomicEvent(
                                    event_type = rec_transfer_et,
                                    event_date = event_date,
                                    resource_type = pay_rt,
                                    exchange = xfer_exchange,
                                    exchange_stage=next_stage,
                                    from_agent = xfer_event.to_agent,
                                    to_agent = xfer_event.from_agent,
                                    context_agent = context_agent,
                                    quantity = value_stage_2,
                                    unit_of_quantity = unit_of_value,
                                    value = value_stage_2,
                                    unit_of_value = unit_of_value,
                                    created_by = request.user,                        
                                )
                                pay_event_2.save()
                        elif paid_stage_2 == "later":
                            if value_stage_2 > 0:
                                commit_2 = Commitment (
                                    commitment_date=event_date,
                                    event_type=pay_et,
                                    exchange=xfer_exchange,
                                    exchange_stage=next_stage,
                                    due_date=event_date,
                                    from_agent=xfer_event.to_agent,
                                    to_agent=rxfer_event.from_agent,
                                    context_agent=context_agent,
                                    resource_type=pay_rt,
                                    quantity=value_stage_2,
                                    unit_of_quantity=unit_of_value,
                                    value=value_stage_2,
                                    unit_of_value=unit_of_value,
                                    created_by=request.user,                        
                                )
                                commit_2.save()
                                                
                        consume_event = EconomicEvent(
                            event_type = consume_et,
                            event_date = event_date,
                            resource = resource,
                            resource_type = resource.resource_type,
                            from_agent = xfer_event.to_agent,
                            to_agent = to_agent,
                            context_agent = context_agent,
                            quantity = quantity,
                            unit_of_quantity = resource.resource_type.unit,
                            created_by = request.user,
                        )
                        consume_event.save()
                        ces.append(consume_event)
                        
            process = Process(
                name="Combined harvested: new lot",
                end_date=event_date,
                start_date=event_date,
                created_by=request.user,
                context_agent=context_agent                 
            )
            process.save()
            for ce in ces:
                ce.process = process
                ce.save()
            prod_resource = EconomicResource(
                identifier=identifier,
                resource_type=commitment.resource_type,
                quantity=quantity,
                exchange_stage=next_stage,
                created_by=request.user                
            )
            prod_resource.save()
            prod_event = EconomicEvent(
                event_type = produce_et,
                event_date = event_date,
                resource = prod_resource,
                resource_type = prod_resource.resource_type,
                process = process,
                from_agent = to_agent,
                to_agent = to_agent,
                context_agent = context_agent,
                quantity = quantity,
                unit_of_quantity = prod_resource.resource_type.unit,
                description=notes,
                created_by = request.user,               
            )
            prod_event.save()
            
            if zero_out == True:
                commitment.finished = True
                commitment.save()
            
            #todo: put skip stage here!
            
    return HttpResponseRedirect('/%s/%s/'
        % ('board/dhen-board', context_agent_id))

@login_required
def transfer_resource(request, context_agent_id, assoc_type_identifier, resource_id=None):
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        resource = EconomicResource.objects.get(id=resource_id)
        stage = AgentAssociationType.objects.get(identifier=assoc_type_identifier)
        #todo: hardcoded recipe and exchange types
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
            lot_form = NewResourceForm(prefix=prefix, data=request.POST)
            identifier = None
            if lot_form:
                lot_data = form.cleaned_data
                identifier = lot_data["identifier"]
            zero_form = ZeroOutForm(prefix=prefix, data=request.POST)
            zero_out = False
            if zero_form:
                zero_data = form.cleaned_data
                zero_out = zero_data["zero_out"]
                
            if identifier:
                process = Process(
                    name="Harvest: new lot",
                    end_date=event_date,
                    start_date=event_date,
                    created_by=request.user,
                    context_agent=context_agent                   
                )
                process.save()
                event_in = EconomicEvent(
                    event_type = EventType.objects.get(name="Resource Consumption"),
                    event_date = event_date,
                    resource = resource,
                    resource_type = resource.resource_type,
                    process = process,
                    from_agent = from_agent,
                    to_agent = to_agent,
                    context_agent = context_agent,
                    quantity = quantity,
                    unit_of_quantity = resource.resource_type.unit,
                    created_by = request.user,
                )
                event_in.save()
                new_resource = EconomicResource(
                    identifier=identifier,
                    resource_type=resource.resource_type,
                    quantity=quantity,
                    exchange_stage=AgentAssociationType.objects.get(identifier="Harvester"),
                    created_by=request.user
                    )
                event_out = EconomicEvent(
                    event_type = EventType.objects.get(name="Resource Production"),
                    event_date = event_date,
                    resource = new_resource,
                    resource_type = resource.resource_type,
                    process = process,
                    from_agent = from_agent,
                    to_agent = to_agent,
                    context_agent = context_agent,
                    quantity = quantity,
                    unit_of_quantity = resource.resource_type.unit,
                    created_by = request.user,
                )
                event_out.save()
                if zero_out == True:
                    resource.quantity = 0
                else:
                    resource.quantity -= quantity
                if resource.quantity < 0:
                    resource.quantity = 0
                resource.save()
                
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
                        quantity = value,
                        unit_of_quantity = unit_of_value,
                        value = value,
                        unit_of_value = unit_of_value,
                        created_by = request.user,                        
                    )
                    rec_xfer_event.save()
            elif paid == "later":
                if value > 0:
                    commit = Commitment (
                        event_type=EventType.objects.get(name="Reciprocal Transfer"),
                        exchange=exchange,
                        due_date=event_date,
                        from_agent=to_agent,
                        to_agent=from_agent,
                        context_agent=context_agent,
                        quantity=quantity,
                        unit_of_value = unit_of_value,
                        created_by=request.user,                        
                    )
                    commit.save()
    return HttpResponseRedirect('/%s/%s/'
        % ('board/dhen-board', context_agent_id))
