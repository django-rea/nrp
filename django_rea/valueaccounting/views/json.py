import simplejson
import datetime
import time

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.http.response import HttpResponse, Http404
from django.core import serializers

from django_rea.valueaccounting.models import *

from django_rea.valueaccounting.logic.recipe import (
    create_events,
    process_graph,
    project_process_resource_agent_graph
)


def json_order_timeline(request, order_id):
    events = {'dateTimeFormat': 'Gregorian', 'events': []}
    order = get_object_or_404(Order, pk=order_id)
    processes = order.all_processes()
    orders = [order, ]
    create_events(orders, processes, events)
    data = simplejson.dumps(events, ensure_ascii=False)
    # import pdb; pdb.set_trace()
    return HttpResponse(data, content_type="text/json-comment-filtered")


def json_processes(request, order_id=None):
    # import pdb; pdb.set_trace()
    if order_id:
        order = get_object_or_404(Order, pk=order_id)
        processes = order.all_processes()
    else:
        processes = Process.objects.unfinished()
    graph = process_graph(processes)
    data = simplejson.dumps(graph)
    return HttpResponse(data, content_type="text/json-comment-filtered")


def json_project_processes(request, object_type=None, object_id=None):
    # import pdb; pdb.set_trace()
    # todo: needs to change
    # project and agent are now both agents
    # active_processes has been fixed, though...
    if object_type:
        if object_type == "P":
            project = get_object_or_404(EconomicAgent, pk=object_id)
            processes = project.active_processes()
            projects = [project, ]
        elif object_type == "O":
            order = get_object_or_404(Order, pk=object_id)
            processes = order.all_processes()
            projects = [p.context_agent for p in processes if p.context_agent]
            projects = list(set(projects))
        elif object_type == "A":
            agent = get_object_or_404(EconomicAgent, pk=object_id)
            processes = agent.active_processes()
            projects = [p.context_agent for p in processes if p.context_agent]
            projects = list(set(projects))
    else:
        processes = Process.objects.unfinished()
        projects = [p.context_agent for p in processes if p.context_agent]
        projects = list(set(projects))
    # import pdb; pdb.set_trace()
    graph = project_process_resource_agent_graph(projects, processes)
    data = simplejson.dumps(graph)
    return HttpResponse(data, content_type="text/json-comment-filtered")


def json_resource_type_unit(request, resource_type_id):
    data = serializers.serialize("json", EconomicResourceType.objects.filter(id=resource_type_id), fields=('unit',))
    return HttpResponse(data, content_type="text/json-comment-filtered")


def json_agent(request, agent_id):
    data = serializers.serialize("json", EconomicAgent.objects.filter(id=agent_id))
    return HttpResponse(data, content_type="text/json-comment-filtered")


def json_resource_type_citation_unit(request, resource_type_id):
    # import pdb; pdb.set_trace()
    ert = get_object_or_404(EconomicResourceType, pk=resource_type_id)
    direction = "use"
    defaults = {
        "unit": ert.directional_unit(direction).name,
    }
    data = simplejson.dumps(defaults, ensure_ascii=False)
    return HttpResponse(data, content_type="text/json-comment-filtered")


def json_directional_unit(request, resource_type_id, direction):
    # import pdb; pdb.set_trace()
    ert = get_object_or_404(EconomicResourceType, pk=resource_type_id)
    defaults = {
        "unit": ert.directional_unit(direction).id,
    }
    data = simplejson.dumps(defaults, ensure_ascii=False)
    return HttpResponse(data, content_type="text/json-comment-filtered")


def json_default_equation(request, event_type_id):
    et = get_object_or_404(EventType, pk=event_type_id)
    equation = et.default_event_value_equation()
    data = simplejson.dumps(equation, ensure_ascii=False)
    return HttpResponse(data, content_type="text/json-comment-filtered")


def json_directional_unit_and_rule(request, resource_type_id, direction):
    # import pdb; pdb.set_trace()
    ert = get_object_or_404(EconomicResourceType, pk=resource_type_id)
    defaults = {
        "unit": ert.directional_unit(direction).id,
        "rule": ert.inventory_rule
    }
    data = simplejson.dumps(defaults, ensure_ascii=False)
    return HttpResponse(data, content_type="text/json-comment-filtered")


def json_resource_type_defaults(request, resource_type_id):
    ert = get_object_or_404(EconomicResourceType, pk=resource_type_id)
    defaults = {
        "unit": ert.unit.id,
    }
    # import pdb; pdb.set_trace()
    data = simplejson.dumps(defaults, ensure_ascii=False)
    return HttpResponse(data, content_type="text/json-comment-filtered")


def json_context_agent_suppliers(request, agent_id):
    # import pdb; pdb.set_trace()
    agent = EconomicAgent.objects.get(id=agent_id)
    json = serializers.serialize("json", agent.all_suppliers(), fields=('pk', 'nick'))
    return HttpResponse(json, content_type='application/json')


def json_context_agent_customers(request, agent_id):
    # import pdb; pdb.set_trace()
    agent = EconomicAgent.objects.get(id=agent_id)
    json = serializers.serialize("json", agent.all_customers(), fields=('pk', 'nick'))
    return HttpResponse(json, content_type='application/json')


def json_order_customer(request, order_id, agent_id):
    # import pdb; pdb.set_trace()
    if order_id == '0':
        agent = EconomicAgent.objects.get(id=agent_id)
        json = serializers.serialize("json", agent.all_customers(), fields=('pk', 'nick'))
    else:
        customers = []
        order = Order.objects.get(id=order_id)
        if order.provider:
            customers.append(order.provider)
        json = serializers.serialize("json", customers, fields=('pk', 'nick'))
    return HttpResponse(json, content_type='application/json')


def json_customer_orders(request, customer_id):
    # import pdb; pdb.set_trace()
    if customer_id == '0':
        os = Order.objects.customer_orders()
    else:
        customer = EconomicAgent.objects.get(id=customer_id)
        os = customer.sales_orders.all()
    orders = []
    for order in os:
        fields = {
            "pk": order.pk,
            "name": str(order)
        }
        orders.append({"fields": fields})
    data = simplejson.dumps(orders, ensure_ascii=False)
    return HttpResponse(data, content_type="text/json-comment-filtered")


def json_context_timeline(request, context_id):
    # import pdb; pdb.set_trace()
    events = {'dateTimeFormat': 'Gregorian', 'events': []}
    context_agent = get_object_or_404(EconomicAgent, pk=context_id)
    processes = Process.objects.unfinished().filter(context_agent=context_agent)
    orders = [p.independent_demand() for p in processes if p.independent_demand()]
    orders = list(set(orders))
    create_events(orders, processes, events)
    data = simplejson.dumps(events, ensure_ascii=False)
    # import pdb; pdb.set_trace()
    return HttpResponse(data, content_type="text/json-comment-filtered")


def json_resource_type_resources(request, resource_type_id):
    # import pdb; pdb.set_trace()
    json = serializers.serialize("json", EconomicResource.objects.filter(resource_type=resource_type_id),
                                 fields=('identifier'))
    return HttpResponse(json, content_type='application/json')


def json_resource_type_stages(request, resource_type_id):
    # import pdb; pdb.set_trace()
    rt = get_object_or_404(EconomicResourceType, pk=resource_type_id)
    json = serializers.serialize("json", rt.all_stages(), fields=('name'))
    return HttpResponse(json, content_type='application/json')


def json_resource_type_resources_with_locations(request, resource_type_id):
    # import pdb; pdb.set_trace()
    rs = EconomicResource.objects.filter(resource_type=resource_type_id)
    resources = []
    for r in rs:
        loc = ""
        if r.current_location:
            loc = r.current_location.name
        fields = {
            "pk": r.pk,
            "identifier": r.identifier,
            "location": loc,
        }
        resources.append({"fields": fields})
    data = simplejson.dumps(resources, ensure_ascii=False)
    return HttpResponse(data, content_type="text/json-comment-filtered")


def json_resource(request, resource_id):
    # import pdb; pdb.set_trace()
    r = get_object_or_404(EconomicResource, pk=resource_id)
    loc = ""
    if r.current_location:
        loc = r.current_location.name
    rdict = {
        "class": "EconomicResource",
        "id": r.id,
        "identifier": r.identifier,
        "location": loc,
        "quantity": str(r.quantity),
        "unit": r.resource_type.unit.name,
        "access_rules": r.access_rules,
    }
    assignments = {}
    for item in r.agent_resource_roles.all():
        assignments[item.role.name] = item.agent.name
    rdict["assignments"] = assignments
    data = simplejson.dumps(rdict)
    return HttpResponse(data, content_type="text/json-comment-filtered")


def json_organization(request):
    # import pdb; pdb.set_trace()
    agent_types = AgentType.objects.all()
    at_dict = {}
    for at in agent_types:
        fields = {
            "name": at.name,
            "is_context": at.is_context,
        }
        at_dict[at.name] = fields
    agents = EconomicAgent.objects.all()
    agent_dict = {}
    for agent in agents:
        fields = {
            "class": "EconomicAgent",
            "pk": agent.pk,
            "id": agent.nick,
            "name": agent.name,
            "agent_type": agent.agent_type.name,
        }
        agent_dict[agent.nick] = fields
    aa_types = AgentAssociationType.objects.all()
    aat_dict = {}
    for aat in aa_types:
        fields = {
            "name": aat.name,
            "plural_name": aat.plural_name,
            "label": aat.label,
            "inverse_label": aat.inverse_label,
            "description": aat.description,
        }
        aat_dict[aat.name] = fields
    associations = AgentAssociation.objects.all()
    assoc_dict = {}
    for a in associations:
        fields = {
            "pk": a.pk,
            "is_associate": a.is_associate.nick,
            "has_associate": a.has_associate.nick,
            "association_type": a.association_type.name,
        }
        assoc_dict[a.pk] = fields
    big_d = {
        "agentTypes": at_dict,
        "agents": agent_dict,
        "agentAssociationTypes": aat_dict,
        "agentAssociations": assoc_dict,
    }
    data = simplejson.dumps(big_d)
    return HttpResponse(data, content_type="text/json-comment-filtered")


def json_distribution_related_shipment(request, distribution_id):
    d = get_object_or_404(EconomicEvent, pk=distribution_id)
    ship = d.get_shipment_for_distribution()
    sd = {}
    if ship:
        sd = {
            "ship_id": ship.id,
            "ship_description": ship.__unicode__(),
        }
    data = simplejson.dumps(sd)
    return HttpResponse(data, content_type="text/json-comment-filtered")


def json_distribution_related_order(request, distribution_id):
    d = get_object_or_404(EconomicEvent, pk=distribution_id)
    # import pdb; pdb.set_trace()
    order = d.get_order_for_distribution()
    od = {}
    if order:
        od = {
            "order_id": order.id,
            "order_description": order.__unicode__(),
        }
    data = simplejson.dumps(od)
    return HttpResponse(data, content_type="text/json-comment-filtered")


def json_timeline(request, from_date, to_date, context_id):
    try:
        start = datetime.datetime(*time.strptime(from_date, '%Y_%m_%d')[0:5]).date()
        end = datetime.datetime(*time.strptime(to_date, '%Y_%m_%d')[0:5]).date()
    except ValueError:
        raise Http404
    context_id = int(context_id)
    context_agent = None
    if context_id:
        context_agent = get_object_or_404(EconomicAgent, pk=context_id)
    events = {'dateTimeFormat': 'Gregorian', 'events': []}
    processes = Process.objects.unfinished().filter(
        Q(start_date__range=(start, end)) | Q(end_date__range=(start, end)) |
        Q(start_date__lt=start, end_date__gt=end))
    if context_agent:
        processes = processes.filter(context_agent=context_agent)
    orders = [p.independent_demand() for p in processes if p.independent_demand()]
    orders = list(set(orders))
    create_events(orders, processes, events)
    data = simplejson.dumps(events, ensure_ascii=False)
    # import pdb; pdb.set_trace()
    return HttpResponse(data, content_type="text/json-comment-filtered")

def json_value_equation_bucket(request, value_equation_id):
    # import pdb; pdb.set_trace()
    ve = ValueEquation.objects.get(id=value_equation_id)
    bkts = ve.buckets.all()
    buckets = []
    for b in bkts:
        agent_name = "null"
        filter_method = "null"
        if b.distribution_agent:
            agent_name = b.distribution_agent.name
        if b.filter_method:
            filter_method = b.filter_method
        fields = {
            "sequence": b.sequence,
            "name": b.name,
            "percentage": b.percentage,
            "agent_name": agent_name,
            "filter_method": filter_method,
        }
        buckets.append({"fields": fields})
    json = simplejson.dumps(buckets, ensure_ascii=False)
    return HttpResponse(json, content_type='application/json')
