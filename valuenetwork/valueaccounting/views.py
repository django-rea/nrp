import datetime
import time
import csv
from operator import attrgetter

from django.db.models import Q
from django.http import Http404
from django.views.generic import list_detail
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseServerError
from django.core import serializers
from django.contrib.auth.decorators import login_required
from django.core.exceptions import MultipleObjectsReturned
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import simplejson
from django.forms.models import formset_factory, modelformset_factory
from django.forms import ValidationError
from django.utils import simplejson

from valuenetwork.valueaccounting.models import *
from valuenetwork.valueaccounting.views import *
from valuenetwork.valueaccounting.forms import *
from valuenetwork.valueaccounting.utils import *

def get_agent(request):
    nick = request.user.username
    if nick:
        try:
            agent = EconomicAgent.objects.get(nick=nick.capitalize)
        except EconomicAgent.DoesNotExist:
            agent = get_object_or_404(EconomicAgent, nick=nick)
    else:
        agent = "Unregistered"
    return agent

def projects(request):
    roots = Project.objects.filter(parent=None)
    
    return render_to_response("valueaccounting/projects.html", {
        "roots": roots,
    }, context_instance=RequestContext(request))

def resource_types(request):
    roots = EconomicResourceType.objects.exclude(materiality="work")
    #roots = EconomicResourceType.objects.all()
    create_form = EconomicResourceTypeForm()
    categories = Category.objects.all()
    select_all = True
    selected_cats = "all"
    if request.method == "POST":
        selected_cats = request.POST["categories"]
        cats = selected_cats.split(",")
        if cats[0] == "all":
            select_all = True
            roots = EconomicResourceType.objects.all()
        else:
            select_all = False
            roots = EconomicResourceType.objects.filter(category__name__in=cats)
        #import pdb; pdb.set_trace()
    return render_to_response("valueaccounting/resource_types.html", {
        "roots": roots,
        "categories": categories,
        "select_all": select_all,
        "selected_cats": selected_cats,
        "create_form": create_form,
        "photo_size": (128, 128),
    }, context_instance=RequestContext(request))

def contributions(request, project_id):
    #import pdb; pdb.set_trace()
    project = get_object_or_404(Project, pk=project_id)
    event_list = project.events.all()
    paginator = Paginator(event_list, 25)

    page = request.GET.get('page')
    try:
        events = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        events = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        events = paginator.page(paginator.num_pages)
    
    return render_to_response("valueaccounting/project_contributions.html", {
        "project": project,
        "events": events,
    }, context_instance=RequestContext(request))

def contribution_history(request, agent_id):
    #import pdb; pdb.set_trace()
    agent = get_object_or_404(EconomicAgent, pk=agent_id)
    event_list = agent.given_events.all()
    paginator = Paginator(event_list, 25)

    page = request.GET.get('page')
    try:
        events = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        events = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        events = paginator.page(paginator.num_pages)
    
    return render_to_response("valueaccounting/agent_contributions.html", {
        "agent": agent,
        "events": events,
    }, context_instance=RequestContext(request))


def log_time(request):
    member = get_agent(request)
    form = TimeForm()
    roots = Project.objects.filter(parent=None)
    resource_types = EconomicResourceType.objects.filter(materiality="work")
    #resource_types = EconomicResourceType.objects.all()
    return render_to_response("valueaccounting/log_time.html", {
        "member": member,
        "form": form,
        "roots": roots,
        "resource_types": resource_types,
    }, context_instance=RequestContext(request))


class EventSummary(object):
    def __init__(self, agent, role, quantity, value=Decimal('0.0')):
        self.agent = agent
        self.role = role
        self.quantity = quantity
        self.value=value

    def key(self):
        return "-".join([str(self.agent.id), str(self.role.id)])

    def quantity_formatted(self):
        return self.quantity.quantize(Decimal('.01'), rounding=ROUND_UP)


class AgentSummary(object):
    def __init__(self, 
        agent, 
        value=Decimal('0.0'), 
        percentage=Decimal('0.0'),
        amount=Decimal('0.0'),
    ):
        self.agent = agent
        self.value=value
        self.percentage=percentage
        self.amount=amount


def value_equation(request, project_id):
    project = get_object_or_404(Project, pk=project_id)    
    if not CachedEventSummary.objects.all().exists():
        summaries = CachedEventSummary.summarize_events(project)
    all_subs = project.with_all_sub_projects()
    summaries = CachedEventSummary.objects.select_related(
        'agent', 'project', 'resource_type').filter(project__in=all_subs).order_by(
        'agent__name', 'project__name', 'resource_type__name')
    total = 0
    agent_totals = []
    init = {"equation": "( hours * ( rate + importance + reputation ) ) + seniority"}
    form = EquationForm(data=request.POST or None,
        initial=init)
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        if form.is_valid():
            data = form.cleaned_data
            equation = data["equation"]
            amount = data["amount"]
            if amount:
                amount = Decimal(amount)
            eq = equation.split(" ")
            for i, x in enumerate(eq):
                try:
                    y = Decimal(x)
                    eq[i] = "".join(["Decimal('", x, "')"])
                except InvalidOperation:
                    continue
            s = " "
            equation = s.join(eq)
            agent_sums = {}
            total = Decimal("0.00")
            safe_list = ['math',]
            safe_dict = dict([ (k, locals().get(k, None)) for k in safe_list ])
            safe_dict['Decimal'] = Decimal
            #import pdb; pdb.set_trace()
            for summary in summaries:
                safe_dict['hours'] = summary.quantity
                safe_dict['rate'] = summary.resource_type_rate
                safe_dict['importance'] = summary.importance
                safe_dict['reputation'] = summary.reputation
                safe_dict['seniority'] = Decimal(summary.agent.seniority())
                #import pdb; pdb.set_trace()
                summary.value = eval(equation, {"__builtins__":None}, safe_dict)
                agent = summary.agent
                if not agent.id in agent_sums:
                    agent_sums[agent.id] = AgentSummary(agent)
                agent_sums[agent.id].value += summary.value
                total += summary.value
            agent_totals = agent_sums.values()
            #import pdb; pdb.set_trace()
            for at in agent_totals:
               pct = at.value / total
               at.value = at.value.quantize(Decimal('.01'), rounding=ROUND_UP)
               at.percentage = ( pct * 100).quantize(Decimal('.01'), rounding=ROUND_UP)
               if amount:
                   at.amount = (amount * pct).quantize(Decimal('.01'), rounding=ROUND_UP)

    paginator = Paginator(summaries, 50)
    page = request.GET.get('page')
    try:
        events = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        events = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        events = paginator.page(paginator.num_pages)
    
    return render_to_response("valueaccounting/value_equation.html", {
        "project": project,
        "events": events,
        "form": form,
        "agent_totals": agent_totals,
        "total": total,
    }, context_instance=RequestContext(request))

def extended_bill(request, resource_type_id):
    rt = get_object_or_404(EconomicResourceType, pk=resource_type_id)
    #import pdb; pdb.set_trace()
    select_all = True
    categories = Category.objects.all()
    if request.method == "POST":
        nodes = generate_xbill(rt)
        depth = 1
        for node in nodes:
            depth = max(depth, node.depth)
        selected_cats = request.POST["categories"]
        cats = selected_cats.split(",")
        selected_depth = int(request.POST['depth'])
        #import pdb; pdb.set_trace()
        if cats[0]:
            if cats[0] == "all":
                select_all = True
            else:
                select_all = False
        for node in nodes:
            node.show = False
            if node.depth <= selected_depth:
                if select_all:
                    node.show = True
                else:
                    cat = node.category()
                    if cat.name in cats:
                        node.show = True
    else:
        nodes = generate_xbill(rt)
        depth = 1
        for node in nodes:
            depth = max(depth, node.depth)
            node.show = True
        selected_depth = depth
        select_all = True
        selected_cats = "all"
    return render_to_response("valueaccounting/extended_bill.html", {
        "resource_type": rt,
        "nodes": nodes,
        "depth": depth,
        "selected_depth": selected_depth,
        "categories": categories,
        "select_all": select_all,
        "selected_cats": selected_cats,
        "photo_size": (128, 128),
        "big_photo_size": (200, 200),
    }, context_instance=RequestContext(request))

@login_required
def edit_extended_bill(request, resource_type_id):
    rt = get_object_or_404(EconomicResourceType, pk=resource_type_id)
    #import pdb; pdb.set_trace()
    nodes = generate_xbill(rt)
    resource_type_form = EconomicResourceTypeForm(instance=rt)
    process_form = XbillProcessTypeForm()
    change_process_form = ChangeProcessTypeForm()
    source_form = AgentResourceTypeForm()
    feature_form = FeatureForm()
    return render_to_response("valueaccounting/edit_xbill.html", {
        "resource_type": rt,
        "nodes": nodes,
        "photo_size": (128, 128),
        "big_photo_size": (200, 200),
        "resource_type_form": resource_type_form,
        "process_form": process_form,
        "change_process_form": change_process_form,
        "source_form": source_form,
        "feature_form": feature_form,
    }, context_instance=RequestContext(request))

@login_required
def change_resource_type(request, resource_type_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        rt = get_object_or_404(EconomicResourceType, pk=resource_type_id)
        form = EconomicResourceTypeForm(request.POST, request.FILES, instance=rt)
        if form.is_valid():
            data = form.cleaned_data
            rt = form.save(commit=False)
            rt.changed_by=request.user
            rt.save()
            next = request.POST.get("next")
            if next:
                return HttpResponseRedirect(next)
            else:
                return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/edit-xbomfg', resource_type_id))
        else:
            raise ValidationError(form.errors)

@login_required
def delete_resource_type_confirmation(request, resource_type_id):
    rt = get_object_or_404(EconomicResourceType, pk=resource_type_id)
    side_effects = False
    if rt.process_types.all():
        side_effects = True
        return render_to_response('valueaccounting/resource_type_delete_confirmation.html', {
            "resource_type": rt,
            "side_effects": side_effects,
            }, context_instance=RequestContext(request))
    else:
        rt.delete()
        return HttpResponseRedirect('/%s/'
            % ('accounting/resources'))

@login_required
def delete_resource_type(request, resource_type_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        rt = get_object_or_404(EconomicResourceType, pk=resource_type_id)
        pts = rt.producing_process_types()
        rt.delete()
        for pt in pts:
            pt.delete()
        next = request.POST.get("next")
        if next:
            return HttpResponseRedirect(next)
        else:
            return HttpResponseRedirect('/%s/'
                % ('accounting/resources'))

@login_required
def delete_order_confirmation(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    if order.producing_commitments():
        sked = []
        reqs = []
        work = []
        tools = []
        for ct in order.producing_commitments():
            schedule_commitment(ct, sked, reqs, work, tools, 0)
            return render_to_response('valueaccounting/order_delete_confirmation.html', {
                "order": order,
                "sked": sked,
                "reqs": reqs,
                "work": work,
                "tools": tools,
            }, context_instance=RequestContext(request))
    else:
        order.delete()
        return HttpResponseRedirect('/%s/'
            % ('accounting/demand'))

@login_required
def delete_order(request, order_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        order = get_object_or_404(Order, pk=order_id)
        trash = []
        for ct in order.producing_commitments():
            collect_trash(ct, trash)
            order.delete()
            for item in trash:
                item.delete()
        next = request.POST.get("next")
        if next:
            return HttpResponseRedirect(next)
        else:
            return HttpResponseRedirect('/%s/'
                % ('accounting/demand'))

def collect_trash(commitment, trash):
    order = commitment.independent_demand
    process = commitment.process
    trash.append(process)
    for inp in process.incoming_commitments():
        resource_type = inp.resource_type
        pcs = resource_type.producing_commitments()
        if pcs:
            for pc in pcs:
                if pc.independent_demand == order:
                    collect_trash(pc, trash)
    return trash

def collect_lower_trash(commitment, trash):
    order = commitment.independent_demand
    resource_type = commitment.resource_type
    pcs = resource_type.producing_commitments()
    if pcs:
        for pc in pcs:
            if pc.independent_demand == order:
                collect_trash(pc, trash)
    return trash

@login_required
def delete_process_input(request, 
        process_input_id, resource_type_id):
    pi = get_object_or_404(ProcessTypeResourceType, pk=process_input_id)
    pi.delete()
    return HttpResponseRedirect('/%s/%s/'
        % ('accounting/edit-xbomfg', resource_type_id))


@login_required
def delete_source(request, 
        source_id, resource_type_id):
    s = get_object_or_404(AgentResourceType, pk=source_id)
    #import pdb; pdb.set_trace()
    s.delete()
    return HttpResponseRedirect('/%s/%s/'
        % ('accounting/edit-xbomfg', resource_type_id))

@login_required
def delete_process_type_confirmation(request, 
        process_type_id, resource_type_id):
    pt = get_object_or_404(ProcessType, pk=process_type_id)
    side_effects = False
    if pt.resource_types.all():
        side_effects = True
        return render_to_response('valueaccounting/process_type_delete_confirmation.html', {
            "process_type": pt,
            "resource_type_id": resource_type_id,
            "side_effects": side_effects,
            }, context_instance=RequestContext(request))
    else:
        pt.delete()
        return HttpResponseRedirect('/%s/%s/'
            % ('accounting/edit-xbomfg', resource_type_id))

@login_required
def delete_feature_confirmation(request, 
        feature_id, resource_type_id):
    ft = get_object_or_404(Feature, pk=feature_id)
    side_effects = False
    if ft.options.all():
        side_effects = True
        return render_to_response('valueaccounting/feature_delete_confirmation.html', {
            "feature": ft,
            "resource_type_id": resource_type_id,
            "side_effects": side_effects,
            }, context_instance=RequestContext(request))
    else:
        ft.delete()
        return HttpResponseRedirect('/%s/%s/'
            % ('accounting/edit-xbomfg', resource_type_id))


@login_required
def delete_process_type(request, process_type_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        pt = get_object_or_404(ProcessType, pk=process_type_id)
        pt.delete()
        next = request.POST.get("next")
        if next:
            return HttpResponseRedirect(next)
        else:
            return HttpResponseRedirect('/%s/'
                % ('accounting/resources'))

@login_required
def delete_feature(request, feature_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        ft = get_object_or_404(Feature, pk=feature_id)
        ft.delete()
        next = request.POST.get("next")
        return HttpResponseRedirect(next)

@login_required
def create_resource_type(request):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        form = EconomicResourceTypeForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            rt = form.save(commit=False)
            rt.created_by=request.user
            rt.save()
            next = request.POST.get("next")
            if next:
                return HttpResponseRedirect(next)
            else:
                return HttpResponseRedirect('/%s/'
                    % ('accounting/resources'))
        else:
            raise ValidationError(form.errors)


@login_required
def create_process_type_input(request, process_type_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        pt = get_object_or_404(ProcessType, pk=process_type_id)
        prefix = pt.xbill_input_prefix()
        form = ProcessTypeResourceTypeForm(request.POST, prefix=prefix)
        #form = ProcessTypeResourceTypeForm(request.POST)
        if form.is_valid():
            ptrt = form.save(commit=False)
            rt = form.cleaned_data["resource_type"]
            ptrt.process_type=pt
            rel = None
            try:
                rel = ResourceRelationship.objects.get(
                    materiality=rt.materiality,
                    related_to="process",
                    direction="in")
            except ResourceRelationship.DoesNotExist:
                pass
            ptrt.relationship = rel
            ptrt.created_by=request.user
            ptrt.save()
            next = request.POST.get("next")
            return HttpResponseRedirect(next)
        else:
            raise ValidationError(form.errors)

@login_required
def create_process_type_feature(request, process_type_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        pt = get_object_or_404(ProcessType, pk=process_type_id)
        form = FeatureForm(request.POST)
        if form.is_valid():
            feature = form.save(commit=False)
            feature.process_type=pt
            rts = pt.produced_resource_types()
            #todo: assuming the feature applies to the first
            # produced_resource_type
            if rts:
                feature.product=rts[0]
            feature.created_by=request.user
            feature.save()
            next = request.POST.get("next")
            return HttpResponseRedirect(next)
        else:
            raise ValidationError(form.errors)

@login_required
def create_options_for_feature(request, feature_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        ft = get_object_or_404(Feature, pk=feature_id)
        form = OptionsForm(feature=ft, data=request.POST)
        if form.is_valid():
            options = eval(form.cleaned_data["options"])
            for option in options:
                rt = EconomicResourceType.objects.get(pk=int(option))
                opt = Option(
                    feature=ft,
                    component=rt)
                opt.created_by=request.user
                opt.save()
                
            next = request.POST.get("next")
            return HttpResponseRedirect(next)
        else:
            raise ValidationError(form.errors)

@login_required
def change_options_for_feature(request, feature_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        ft = get_object_or_404(Feature, pk=feature_id)
        form = OptionsForm(feature=ft, data=request.POST)
        if form.is_valid():
            options = form.cleaned_data["options"]
            selected_options = []
            if options:
                selected_options = eval(form.cleaned_data["options"])
                selected_options = [int(opt) for opt in selected_options]
            previous_options = ft.options.all()
            previous_ids = ft.options.values_list('component__id', flat=True)
            for option in previous_options:
                if not option.component.id in selected_options:
                    option.delete()
            for option in selected_options:
                if not option in previous_ids:
                    rt = EconomicResourceType.objects.get(pk=int(option))
                    opt = Option(
                        feature=ft,
                        component=rt)
                    opt.created_by=request.user
                    opt.save()
                
            next = request.POST.get("next")
            return HttpResponseRedirect(next)
        else:
            raise ValidationError(form.errors)

@login_required
def change_process_type_input(request, input_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        ptrt = get_object_or_404(ProcessTypeResourceType, pk=input_id)
        prefix = ptrt.xbill_change_prefix()
        form = ProcessTypeResourceTypeForm(
            data=request.POST, 
            instance=ptrt,
            prefix=prefix)
        #form = ProcessTypeResourceTypeForm(
        #    data=request.POST, 
        #    instance=ptrt)
        if form.is_valid():
            inp = form.save(commit=False)
            inp.changed_by=request.user
            inp.save()
            next = request.POST.get("next")
            return HttpResponseRedirect(next)
        else:
            raise ValidationError(form.errors)

@login_required
def change_agent_resource_type(request, agent_resource_type_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        art = get_object_or_404(AgentResourceType, pk=agent_resource_type_id)
        #prefix = art.xbill_change_prefix()
        #form = AgentResourceTypeForm(data=request.POST, instance=art, prefix=prefix)
        form = AgentResourceTypeForm(data=request.POST, instance=art)
        if form.is_valid():
            art = form.save(commit=False)
            art.changed_by=request.user
            art.save()
            next = request.POST.get("next")
            return HttpResponseRedirect(next)
        else:
            raise ValidationError(form.errors)

@login_required
def change_feature(request, feature_id):
    if request.method == "POST":
        ft = get_object_or_404(Feature, pk=feature_id)
        #prefix = ft.xbill_change_prefix()
        #form = FeatureForm(data=request.POST, instance=ft, prefix=prefix)
        form = FeatureForm(data=request.POST, instance=ft)
        if form.is_valid():
            feature = form.save(commit=False)
            feature.changed_by=request.user
            feature.save()
            next = request.POST.get("next")
            return HttpResponseRedirect(next)
        else:
            raise ValidationError(form.errors)


@login_required
def create_agent_resource_type(request, resource_type_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        rt = get_object_or_404(EconomicResourceType, pk=resource_type_id)
        form = AgentResourceTypeForm(request.POST)
        if form.is_valid():
            art = form.save(commit=False)
            art.resource_type=rt
            rel = None
            try:
                rel = ResourceRelationship.objects.get(
                    materiality=rt.materiality,
                    related_to="agent",
                    direction="out")
            except ResourceRelationship.DoesNotExist:
                pass
            art.relationship = rel
            art.created_by=request.user
            art.save()
            next = request.POST.get("next")
            return HttpResponseRedirect(next)
        else:
            raise ValidationError(form.errors)

@login_required
def change_process_type(request, process_type_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        pt = get_object_or_404(ProcessType, pk=process_type_id)
        #prefix = pt.xbill_change_prefix()
        #form = ChangeProcessTypeForm(request.POST, instance=pt, prefix=prefix)
        form = ChangeProcessTypeForm(request.POST, instance=pt)
        if form.is_valid():
            pt = form.save(commit=False)
            pt.changed_by=request.user
            pt.save()
            next = request.POST.get("next")
            return HttpResponseRedirect(next)
        else:
            raise ValidationError(form.errors)

@login_required
def create_process_type_for_resource_type(request, resource_type_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        rt = get_object_or_404(EconomicResourceType, pk=resource_type_id)
        form = XbillProcessTypeForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            pt = form.save(commit=False)
            pt.changed_by=request.user
            pt.save()
            quantity = data["quantity"]
            rel = ResourceRelationship.objects.get(
                materiality=rt.materiality,
                related_to="process",
                direction="out")
            unit = rt.unit
            quantity = Decimal(quantity)
            ptrt = ProcessTypeResourceType(
                process_type=pt,
                resource_type=rt,
                relationship=rel,
                unit_of_quantity=unit,
                quantity=quantity,
                created_by=request.user,
            )
            ptrt.save()
            next = request.POST.get("next")
            return HttpResponseRedirect(next)
        else:
            raise ValidationError(form.errors)

def network(request, resource_type_id):
    #import pdb; pdb.set_trace()
    rt = get_object_or_404(EconomicResourceType, pk=resource_type_id)
    nodes, edges = graphify(rt, 3)
    return render_to_response("valueaccounting/network.html", {
        "resource_type": rt,
        "photo_size": (128, 128),
        "nodes": nodes,
        "edges": edges,
    }, context_instance=RequestContext(request))

def project_network(request):
    producers = [p for p in ProcessType.objects.all() if p.produced_resource_types()]
    nodes, edges = project_graph(producers)
    return render_to_response("valueaccounting/network.html", {
        "photo_size": (128, 128),
        "nodes": nodes,
        "edges": edges,
    }, context_instance=RequestContext(request))

def timeline(request):
    timeline_date = datetime.date.today().strftime("%b %e %Y 00:00:00 GMT-0600")
    unassigned = Commitment.objects.filter(
        from_agent=None,
        resource_type__materiality="work").order_by("due_date")
    return render_to_response("valueaccounting/timeline.html", {
        "timeline_date": timeline_date,
        "unassigned": unassigned,
    }, context_instance=RequestContext(request))

def json_timeline(request):
    #data = "{ 'wiki-url':'http://simile.mit.edu/shelf/', 'wiki-section':'Simile JFK Timeline', 'dateTimeFormat': 'Gregorian','events': [{'start':'May 28 2006 09:00:00 GMT-0600','title': 'Writing Timeline documentation','link':'http://google.com','description':'Write some doc already','durationEvent':false }, {'start': 'Jun 16 2006 00:00:00 GMT-0600' ,'end':  'Jun 26 2006 00:00:00 GMT-0600' ,'durationEvent':true,'title':'Friends wedding'}]}"
    #import pdb; pdb.set_trace()
    #orders = Order.objects.all()
    #processes = []
    #for order in orders:
    #    for commitment in order.producing_commitments():
    #        processes.append(commitment.process)
    events = {'dateTimeFormat': 'Gregorian','events':[]}
    #for process in processes:
    #    backschedule_events(process, events)
    #for order in orders:
    #    backschedule_order(order, events)
    orders = Order.objects.all()
    processes = Process.objects.all()
    create_events(orders, processes, events)
    data = simplejson.dumps(events, ensure_ascii=False)
    return HttpResponse(data, mimetype="text/json-comment-filtered")

def json_resource_type_unit(request, resource_type_id):
    data = serializers.serialize("json", EconomicResourceType.objects.filter(id=resource_type_id), fields=('unit',))
    return HttpResponse(data, mimetype="text/json-comment-filtered")

def json_directional_unit(request, resource_type_id, direction):
    #import pdb; pdb.set_trace()
    ert = get_object_or_404(EconomicResourceType, pk=resource_type_id)
    defaults = {
        "unit": ert.directional_unit(direction).id,
    }
    data = simplejson.dumps(defaults, ensure_ascii=False)
    return HttpResponse(data, mimetype="text/json-comment-filtered")

def json_resource_type_defaults(request, resource_type_id):
    ert = get_object_or_404(EconomicResourceType, pk=resource_type_id)
    defaults = {
        "unit": ert.unit.id,
    }
    #import pdb; pdb.set_trace()
    data = simplejson.dumps(defaults, ensure_ascii=False)
    return HttpResponse(data, mimetype="text/json-comment-filtered")

@login_required
def create_order(request):
    cats = Category.objects.filter(orderable=True)
    rts = EconomicResourceType.objects.filter(category__in=cats)
    item_forms = []
    data = request.POST or None
    order_form = OrderForm(data=data)
    for rt in rts:
        prefix1 = "-".join(['RT', str(rt.id)])
        init = {'resource_type_id': rt.id,}
        form = OrderItemForm(data=data, prefix=prefix1, resource_type=rt, initial=init)
        form.features = []
        for ft in rt.features.all():
            prefix2 = "-".join(['FT', str(ft.id)])
            form.features.append(OrderItemOptionsForm(data=data, prefix=prefix2, feature=ft))
        item_forms.append(form)
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        if order_form.is_valid():
            order = order_form.save(commit=False)
            order.created_by=request.user
            order.order_type = "customer"
            order.save()
            #import pdb; pdb.set_trace()
            for form in item_forms:
                if form.is_valid():
                    data = form.cleaned_data
                    qty = data["quantity"]
                    if qty:
                        rt_id = data["resource_type_id"]
                        rt = EconomicResourceType.objects.get(id=rt_id)
                        pt = rt.main_producing_process_type()
                        ptrt = rt.main_producing_process_type_relationship()

                        start_date = order.due_date - datetime.timedelta(minutes=pt.estimated_duration)
                        process = Process(
                            name=pt.name,
                            process_type=pt,
                            project=pt.project,
                            url=pt.url,
                            end_date=order.due_date,
                            start_date=start_date,
                            owner=order.provider,
                            managed_by=order.provider,
                            created_by=request.user,
                        )
                        process.save()
                        commitment = Commitment(
                            order=order,
                            independent_demand=order,
                            event_type=ptrt.relationship.event_type,
                            relationship=ptrt.relationship,
                            due_date=order.due_date,
                            from_agent_type=order.provider.agent_type,
                            from_agent=order.provider,
                            to_agent=order.receiver,
                            resource_type=rt,
                            process=process,
                            project=pt.project,
                            description=data["description"],
                            quantity=qty,
                            unit_of_quantity=rt.unit,
                            created_by=request.user,
                        )
                        commitment.save()
                        for ftr in form.features:
                            if ftr.is_valid():
                                option_id = ftr.cleaned_data["options"]
                                option = Option.objects.get(id=option_id)
                                component = option.component
                                feature = ftr.feature
                                process_type = feature.process_type
                                #import pdb; pdb.set_trace()
                                if process_type != pt:
                                    raise ValueError(process_type)
                                commitment = Commitment(
                                    independent_demand=order,
                                    event_type=feature.relationship.event_type,
                                    relationship=feature.relationship,
                                    due_date=process.start_date,
                                    to_agent=order.provider,
                                    resource_type=component,
                                    process=process,
                                    project=pt.project,
                                    quantity=qty * feature.quantity,
                                    unit_of_quantity=component.unit,
                                    created_by=request.user,
                                )
                                commitment.save()
                                pptr = component.main_producing_process_type_relationship()
                                if pptr:
                                    next_pt = pptr.process_type
                                    start_date = process.start_date - datetime.timedelta(minutes=next_pt.estimated_duration)
                                    next_process = Process(          
                                        name=next_pt.name,
                                        process_type=next_pt,
                                        project=next_pt.project,
                                        url=next_pt.url,
                                        end_date=process.start_date,
                                        start_date=start_date,
                                        created_by=request.user,
                                    )
                                    next_process.save()
                                    next_commitment = Commitment(
                                        independent_demand=order,
                                        event_type=pptr.relationship.event_type,
                                        relationship=pptr.relationship,
                                        due_date=process.start_date,
                                        resource_type=pptr.resource_type,
                                        process=next_process,
                                        project=next_pt.project,
                                        quantity=qty * feature.quantity,
                                        unit_of_quantity=pptr.resource_type.unit,
                                        created_by=request.user,
                                    )
                                    next_commitment.save()
                                    generate_schedule(next_process, order, request.user)
                        generate_schedule(process, order, request.user)
                        return HttpResponseRedirect('/%s/%s/'
                            % ('accounting/order-schedule', order.id))
                     
    return render_to_response("valueaccounting/create_order.html", {
        "order_form": order_form,
        "item_forms": item_forms,
    }, context_instance=RequestContext(request))

def schedule_commitment(
        commitment, 
        schedule, 
        reqs, 
        work, 
        tools, 
        depth):
    order = commitment.independent_demand
    commitment.depth = depth * 2
    schedule.append(commitment)
    process = commitment.process
    process.depth = depth * 2
    schedule.append(process)
    #import pdb; pdb.set_trace()
    for inp in process.incoming_commitments():
        inp.depth = depth * 2
        schedule.append(inp)
        resource_type = inp.resource_type
        pcs = resource_type.producing_commitments()
        if pcs:
            for pc in pcs:
                if pc.independent_demand == order:
                    schedule_commitment(pc, schedule, reqs, work, tools, depth+1)
        elif inp.independent_demand == order:
            if resource_type.materiality == 'material':
                reqs.append(inp)
            elif resource_type.materiality == 'work':
                work.append(inp)
            elif resource_type.materiality == 'tool':
                tools.append(inp)
            for art in resource_type.producing_agent_relationships():
                art.depth = (depth + 1) * 2
                schedule.append(art)

    return schedule

def order_schedule(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    sked = []
    reqs = []
    work = []
    tools = []
    for ct in order.producing_commitments():
        schedule_commitment(ct, sked, reqs, work, tools, 0)
    return render_to_response("valueaccounting/order_schedule.html", {
        "order": order,
        "sked": sked,
        "reqs": reqs,
        "work": work,
        "tools": tools,
    }, context_instance=RequestContext(request))

def demand(request):
    orders = Order.objects.filter(order_type='customer')
    rands = Order.objects.filter(order_type='rand')
    return render_to_response("valueaccounting/demand.html", {
        "orders": orders,
        "rands": rands,
    }, context_instance=RequestContext(request))

def supply(request):
    reqs = []
    commitments = Commitment.objects.filter(resource_type__materiality="material")
    for commitment in commitments:
        if not commitment.resource_type.producing_commitments():
            reqs.append(commitment)
    return render_to_response("valueaccounting/supply.html", {
        "reqs": reqs,
    }, context_instance=RequestContext(request))

def work(request):
    my_work = []
    my_skillz = []
    other_wip = []
    agent = get_agent(request)
    if not agent == "Unregistered":
        my_work = Commitment.objects.filter(
            resource_type__materiality="work",
            from_agent=agent)
        skill_ids = agent.resource_types.values_list('resource_type__id', flat=True)
        my_skillz = Commitment.objects.filter(
            from_agent=None, 
            resource_type__materiality="work",
            resource_type__id__in=skill_ids)
        other_unassigned = Commitment.objects.filter(
            from_agent=None, 
            resource_type__materiality="work").exclude(resource_type__id__in=skill_ids)
        other_wip = Commitment.objects.filter(
            resource_type__materiality="work").exclude(from_agent=None).exclude(from_agent=agent)
    else:
        other_unassigned = Commitment.objects.filter(
            from_agent=None, 
            resource_type__materiality="work")

    #for commitment in commitments:
    #    if not commitment.resource_type.producing_commitments():
    #        work.append(commitment)
    return render_to_response("valueaccounting/work.html", {
        "my_work": my_work,
        "my_skillz": my_skillz,
        "other_unassigned": other_unassigned,
        "other_wip": other_wip,
    }, context_instance=RequestContext(request))


def commit_to_task(request, commitment_id):
    if request.method == "POST":
        ct = get_object_or_404(Commitment, id=commitment_id)
        process = ct.process
        agent = get_agent(request)
        prefix = ct.form_prefix()
        form = CommitmentForm(data=request.POST, prefix=prefix)
        #form = CommitmentForm(data=request.POST)
        #import pdb; pdb.set_trace()
        if form.is_valid():
            data = form.cleaned_data
            #todo: next line did not work, don't want to take time to figure out why right now
            #ct = form.save(commit=False)
            start_date = data["start_date"]
            description = data["description"]
            quantity = data["quantity"]
            unit_of_quantity = data["unit_of_quantity"]
            ct.start_date=start_date
            ct.quantity=quantity
            ct.unit_of_quantity=unit_of_quantity
            ct.description=description
            ct.from_agent = agent
            ct.created_by=request.user
            ct.save()
            if start_date != process.start_date:
                process.start_date = start_date
                process.changed_by=request.user
                process.save()
        next = request.POST.get("next")
        return HttpResponseRedirect(next)

def work_commitment(request, commitment_id):
    ct = get_object_or_404(Commitment, id=commitment_id)
    event = None
    duration = 0
    description = ""
    prev = ""
    today = datetime.date.today()
    events = ct.fulfillment_events.filter(event_date=today)
    if events:
        event = events[events.count() - 1]
        wb_form = WorkbookForm(instance=event, data=request.POST or None)
        duration = event.quantity * 60
        prev_events = ct.fulfillment_events.filter(event_date__lt=today)
        if prev_events:
            prev_dur = sum(prev.quantity for prev in prev_events)
            unit = ""
            if ct.unit_of_quantity:
                unit = ct.unit_of_quantity.name
            prev = " ".join([str(prev_dur), unit])
    else:
        init = {"description": ct.description,}
        wb_form = WorkbookForm(initial=init, data=request.POST or None)
    others_working = []
    wrqs = ct.process.work_requirements()
    if wrqs.count() > 1:
        for wrq in wrqs:
            if not wrq.from_agent is ct.from_agent:
                others_working.append(wrq)
    failure_form = FailedOutputForm()
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        if wb_form.is_valid():
            data = wb_form.cleaned_data
            if event:
                wb_form.save(commit=False)
                event.event_date = today
                event.changed_by = request.user
            else:
                process = ct.process
                if not process.started:
                    process.started = today
                    process.changed_by=request.user
                    process.save()
                event = wb_form.save(commit=False)
                event.commitment = ct
                event.event_date = today
                event.event_type = ct.event_type
                event.from_agent = ct.from_agent
                event.resource_type = ct.resource_type
                event.process = process
                event.project = ct.project
                event.unit_of_quantity = ct.unit_of_quantity
                event.created_by = request.user
                event.changed_by = request.user
                
            event.save()
            description = data["description"]
            if description != ct.description:
                ct.description = description
                ct.save()
            return HttpResponseRedirect('/%s/'
                % ('accounting/work'))
    return render_to_response("valueaccounting/workbook.html", {
        "commitment": ct,
        "process": ct.process,
        "wb_form": wb_form,
        "others_working": others_working,
        "today": today,
        "failure_form": failure_form,
        "duration": duration,
        "prev": prev,
        #"description": description,
    }, context_instance=RequestContext(request))


@login_required
def save_labnotes(request, commitment_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        ct = get_object_or_404(Commitment, id=commitment_id)
        event = None
        today = datetime.date.today()
        events = ct.fulfillment_events.filter(event_date=today)
        if events:
            event = events[events.count() - 1]
            form = WorkbookForm(instance=event, data=request.POST)
        else:
            form = WorkbookForm(data=request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if event:
                event = form.save(commit=False)
                event.changed_by = request.user
            else:
                event = form.save(commit=False)
                event.event_date = today
                event.commitment = ct
                event.process = ct.process
                event.project = ct.project
                event.event_type = ct.event_type
                event.resource_type = ct.resource_type
                event.from_agent = ct.from_agent
                event.to_agent = ct.to_agent
                event.unit_of_quantity = ct.unit_of_quantity
                event.created_by = request.user
                event.changed_by = request.user
                process = ct.process
                if not process.started:
                    process.started = today
                    process.changed_by=request.user
                    process.save()
            event.save()
            description = data["description"]
            if description != ct.description:
                ct.description = description
                ct.save()

            data = "ok"
        else:
            data = form.errors
        return HttpResponse(data, mimetype="text/plain")

def process_details(request, process_id):
    process = get_object_or_404(Process, id=process_id)
    labnotes = False
    if process.work_events():
        labnotes = True
    return render_to_response("valueaccounting/process.html", {
        "process": process,
        "labnotes": labnotes,
    }, context_instance=RequestContext(request))

def labnotes(request, process_id):
    process = get_object_or_404(Process, id=process_id)
    return render_to_response("valueaccounting/labnotes.html", {
        "process": process,
    }, context_instance=RequestContext(request))

def production_event_for_commitment(request):
    id = request.POST.get("id")
    quantity = request.POST.get("quantity")
    ct = get_object_or_404(Commitment, pk=id)
    #import pdb; pdb.set_trace()
    quantity = Decimal(quantity)
    event = None
    events = ct.fulfillment_events.all()
    today = datetime.date.today()
    if events:
        event = events[events.count() - 1]
    if event:
        if event.quantity != quantity:
            event.quantity = quantity
            event.changed_by = request.user
            event.save()
            resource = event.resource
            resource.quantity = quantity
            resource.changed_by=request.user
            resource.save()
    else:
        #todo: resource creation shd depend on event_type and maybe rt
        #design docs will need special handling (url)
        resource = EconomicResource(
            resource_type = ct.resource_type,
            created_date = today,
            quantity = quantity,
            unit_of_quantity = ct.unit_of_quantity,
            created_by=request.user,
        )
        resource.save()
        event = EconomicEvent(
            resource = resource,
            commitment = ct,
            event_date = today,
            event_type = ct.event_type,
            from_agent = ct.from_agent,
            resource_type = ct.resource_type,
            process = ct.process,
            project = ct.project,
            quantity = quantity,
            unit_of_quantity = ct.unit_of_quantity,
            created_by = request.user,
            changed_by = request.user,
        )
        event.save()

    data = "ok"
    return HttpResponse(data, mimetype="text/plain")

#todo: how to handle splits?
def consumption_event_for_commitment(request):
    id = request.POST.get("id")
    quantity = request.POST.get("quantity")
    ct = get_object_or_404(Commitment, pk=id)
    #import pdb; pdb.set_trace()
    quantity = Decimal(quantity)
    event = None
    events = ct.fulfillment_events.all()
    today = datetime.date.today()
    if events:
        event = events[events.count() - 1]
    if event:
        if event.quantity != quantity:
            delta = event.quantity - quantity
            event.quantity = quantity
            event.changed_by = request.user
            event.save()
            resource = event.resource
            resource.quantity += delta
            resource.changed_by=request.user
            resource.save()
    else:
        resources = ct.resource_type.onhand()
        if resources:
            #todo: what if > 1? what if none?
            resource = resources[0]
            #what if resource.quantity < quantity?
            # = handled in template
            resource.quantity -= quantity
            resource.changed_by=request.user
            resource.save()
            event = EconomicEvent(
                resource = resource,
                commitment = ct,
                event_date = today,
                event_type = ct.event_type,
                from_agent = ct.from_agent,
                resource_type = ct.resource_type,
                process = ct.process,
                project = ct.project,
                quantity = quantity,
                unit_of_quantity = ct.unit_of_quantity,
                created_by = request.user,
                changed_by = request.user,
            )
            event.save()

    data = "ok"
    return HttpResponse(data, mimetype="text/plain")

def failed_outputs(request, commitment_id):
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        failure_form = FailedOutputForm(data=request.POST)
        if failure_form.is_valid():
            today = datetime.date.today()
            ct = get_object_or_404(Commitment, id=commitment_id)
            resource_type = ct.resource_type
            process = ct.process
            event = failure_form.save(commit=False)
            data = failure_form.cleaned_data
            quantity = data["quantity"]
            description = data["description"]
            unit_type = resource_type.unit.unit_type
            ets = EventType.objects.filter(
                resource_effect="?",
                unit_type=unit_type)
            if ets:
                event_type = ets[0]
            else:
                et_name = " ".join(["Failed", unit_type])
                event_type = EventType(
                    name=et_name,
                    resource_effect="?",
                    unit_type=unit_type)
                event_type.save()
            resource = EconomicResource(
                resource_type = ct.resource_type,
                created_date = today,
                quantity = quantity,
                quality = Decimal("-1"),
                unit_of_quantity = ct.unit_of_quantity,
                notes = description,
                created_by=request.user,
            )
            resource.save() 
            event.resource = resource              
            event.event_date = today
            event.event_type = event_type
            event.from_agent = ct.from_agent
            event.resource_type = ct.resource_type
            event.process = process
            event.project = ct.project
            event.unit_of_quantity = ct.unit_of_quantity
            event.quality = Decimal("-1")
            event.created_by = request.user
            event.changed_by = request.user
            event.save()
            data = unicode(process.failed_outputs())
            return HttpResponse(data, mimetype="text/plain")

@login_required
def create_process(request):
    #import pdb; pdb.set_trace()
    demand_form = DemandSelectionForm(data=request.POST or None)
    process_form = ProcessForm(data=request.POST or None)
    OutputFormSet = modelformset_factory(
        Commitment,
        form=ProcessOutputForm,
        can_delete=True,
        extra=2,
        )
    output_formset = OutputFormSet(
        queryset=Commitment.objects.none(),
        data=request.POST or None,
        prefix='output')
    InputFormSet = modelformset_factory(
        Commitment,
        form=ProcessInputForm,
        can_delete=True,
        extra=4,
        )
    input_formset = InputFormSet(
        queryset=Commitment.objects.none(),
        data=request.POST or None,
        prefix='input')
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        keep_going = request.POST.get("keep-going")
        just_save = request.POST.get("save")
        if process_form.is_valid():
            process_data = process_form.cleaned_data
            process = process_form.save(commit=False)
            process.created_by=request.user
            process.save()
            demand = None
            if demand_form.is_valid():
                demand = demand_form.cleaned_data["demand"]
            for form in output_formset.forms:
                if form.is_valid():
                    output_data = form.cleaned_data
                    qty = output_data["quantity"]
                    if qty:
                        ct = form.save(commit=False)
                        rt = output_data["resource_type"]
                        rel = ResourceRelationship.objects.get(
                            materiality=rt.materiality,
                            related_to="process",
                            direction="out")
                        ct.relationship = rel
                        ct.event_type = rel.event_type
                        ct.process = process
                        ct.project = process.project
                        ct.independent_demand = demand
                        ct.due_date = process.end_date
                        ct.created_by = request.user
                        ct.save()
            for form in input_formset.forms:
                if form.is_valid():
                    input_data = form.cleaned_data
                    qty = input_data["quantity"]
                    if qty:
                        ct = form.save(commit=False)
                        rt = input_data["resource_type"]
                        rel = ResourceRelationship.objects.get(
                            materiality=rt.materiality,
                            related_to="process",
                            direction="in")
                        ct.relationship = rel
                        ct.event_type = rel.event_type
                        ct.process = process
                        ct.independent_demand = demand
                        ct.due_date = process.start_date
                        ct.created_by = request.user
                        rt = ct.resource_type
                        ptrt = rt.main_producing_process_type_relationship()
                        ct.save()


                        if ptrt:
                            pt = ptrt.process_type
                            start_date = process.start_date - datetime.timedelta(minutes=pt.estimated_duration)
                            feeder_process = Process(
                                name=pt.name,
                                process_type=pt,
                                project=pt.project,
                                url=pt.url,
                                end_date=process.start_date,
                                start_date=start_date,
                                created_by=request.user,
                            )
                            feeder_process.save()
                            output_commitment = Commitment(
                                independent_demand = demand,
                                event_type=ptrt.relationship.event_type,
                                relationship=ptrt.relationship,
                                due_date=process.start_date,
                                resource_type=rt,
                                process=feeder_process,
                                project=pt.project,
                                quantity=qty,
                                unit_of_quantity=rt.unit,
                                created_by=request.user,
                            )
                            output_commitment.save()
                            generate_schedule(feeder_process, demand, request.user)
            return HttpResponseRedirect('/%s/%s/'
                % ('accounting/process', process.id))
    return render_to_response("valueaccounting/create_process.html", {
        "demand_form": demand_form,
        "process_form": process_form,
        "output_formset": output_formset,
        "input_formset": input_formset,
    }, context_instance=RequestContext(request))

@login_required
def change_process(request, process_id):
    #todo: needs to be able add independent demand
    #import pdb; pdb.set_trace()
    process = get_object_or_404(Process, id=process_id)
    process_form = ProcessForm(instance=process, data=request.POST or None)
    OutputFormSet = modelformset_factory(
        Commitment,
        form=ProcessOutputForm,
        can_delete=True,
        extra=2,
        )
    output_formset = OutputFormSet(
        queryset=process.outgoing_commitments(),
        data=request.POST or None,
        prefix='output')
    InputFormSet = modelformset_factory(
        Commitment,
        form=ProcessInputForm,
        can_delete=True,
        extra=4,
        )
    input_formset = InputFormSet(
        queryset=process.incoming_commitments(),
        data=request.POST or None,
        prefix='input')
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        keep_going = request.POST.get("keep-going")
        just_save = request.POST.get("save")
        if process_form.is_valid():
            process_data = process_form.cleaned_data
            process = process_form.save(commit=False)
            process.changed_by=request.user
            process.save()
            demand = process.independent_demand()
            for form in output_formset.forms:
                if form.is_valid():
                    output_data = form.cleaned_data
                    qty = output_data["quantity"]
                    ct_from_id = output_data["id"]
                    if qty:
                        ct = form.save(commit=False)
                        if ct_from_id:
                            ct.project = process.project
                            ct.changed_by = request.user
                        else:
                            ct.process = process
                            ct.project = process.project
                            ct.due_date = process.end_date
                            ct.created_by = request.user
                            rt = output_data["resource_type"]
                            rel = ResourceRelationship.objects.get(
                                materiality=rt.materiality,
                                related_to="process",
                                direction="out")
                            ct.relationship = rel
                            ct.event_type = rel.event_type
                        ct.save()
                    elif ct_from_id:
                        ct = form.save()
                        ct.delete()
            for form in input_formset.forms:
                #import pdb; pdb.set_trace()
                if form.is_valid():
                    explode = False
                    input_data = form.cleaned_data
                    qty = input_data["quantity"]
                    ct_from_id = input_data["id"]
                    if not qty:
                        if ct_from_id:
                            ct = form.save()
                            trash = []
                            collect_lower_trash(ct, trash)
                            for process in trash:
                                if process.outgoing_commitments().count() <= 1:
                                    process.delete()
                            ct.delete()
                    else:
                        ct = form.save(commit=False)
                        if ct_from_id:
                            old_ct = Commitment.objects.get(id=ct_from_id.id)
                            old_rt = old_ct.resource_type
                            if ct.resource_type != old_rt:
                                old_ct.delete()
                                for ex_ct in old_rt.producing_commitments():
                                    if demand == ex_ct.independent_demand:
                                        trash = []
                                        collect_trash(ex_ct, trash)
                                        for process in trash:
                                            #todo: feeder process with >1 outputs 
                                            # shd find the correct output to delete
                                            # and keep the others
                                            if process.outgoing_commitments().count() <= 1:
                                                process.delete()
                                explode = True                                 
                            elif qty != old_ct.quantity:
                                delta = qty - old_ct.quantity
                                for pc in ct.resource_type.producing_commitments():
                                    if pc.independent_demand == demand:
                                        propagate_qty_change(pc, delta)                                
                            ct.changed_by = request.user
                            rt = input_data["resource_type"]
                            rel = ResourceRelationship.objects.get(
                                materiality=rt.materiality,
                                related_to="process",
                                direction="in")
                            ct.relationship = rel
                            ct.event_type = rel.event_type
                        else:
                            explode = True
                            rt = input_data["resource_type"]
                            rel = ResourceRelationship.objects.get(
                                materiality=rt.materiality,
                                related_to="process",
                                direction="in")
                            ct.relationship = rel
                            ct.event_type = rel.event_type
                            ct.process = process
                            ct.independent_demand = demand
                            ct.due_date = process.start_date
                            ct.created_by = request.user
                            ptrt = ct.resource_type.main_producing_process_type_relationship()
                            if ptrt:
                                ct.project = ptrt.process_type.project
                        ct.save()
                        if explode:
                            rt = ct.resource_type
                            ptrt = rt.main_producing_process_type_relationship()
                            if ptrt:
                                pt = ptrt.process_type
                                start_date = process.start_date - datetime.timedelta(minutes=pt.estimated_duration)
                                feeder_process = Process(
                                    name=pt.name,
                                    process_type=pt,
                                    project=pt.project,
                                    url=pt.url,
                                    end_date=process.start_date,
                                    start_date=start_date,
                                    created_by=request.user,
                                )
                                feeder_process.save()
                                output_commitment = Commitment(
                                    independent_demand = demand,
                                    event_type=ptrt.relationship.event_type,
                                    relationship=ptrt.relationship,
                                    due_date=process.start_date,
                                    resource_type=rt,
                                    process=feeder_process,
                                    project=pt.project,
                                    quantity=qty,
                                    unit_of_quantity=rt.unit,
                                    created_by=request.user,
                                )
                                output_commitment.save()
                                generate_schedule(feeder_process, demand, request.user)
            return HttpResponseRedirect('/%s/%s/'
                % ('accounting/process', process.id))
    return render_to_response("valueaccounting/change_process.html", {
        "process": process,
        "process_form": process_form,
        "output_formset": output_formset,
        "input_formset": input_formset,
    }, context_instance=RequestContext(request))

def propagate_qty_change(commitment, delta):
    #import pdb; pdb.set_trace()
    process = commitment.process
    for ic in process.incoming_commitments():
        ratio = ic.quantity / commitment.quantity 
        new_delta = (delta * ratio).quantize(Decimal('.01'), rounding=ROUND_UP)
        ic.quantity += new_delta
        ic.save()
        rt = ic.resource_type
        demand = ic.independent_demand
        for pc in rt.producing_commitments():
            if pc.independent_demand == demand:
                propagate_qty_change(pc, new_delta)
    commitment.quantity += delta
    commitment.save()     

@login_required
def create_rand(request):
    #import pdb; pdb.set_trace()
    rand_form = RandOrderForm(data=request.POST or None)
    process_form = ProcessForm(data=request.POST or None)
    OutputFormSet = modelformset_factory(
        Commitment,
        form=ProcessOutputForm,
        can_delete=True,
        extra=2,
        )
    output_formset = OutputFormSet(
        queryset=Commitment.objects.none(),
        data=request.POST or None,
        prefix='output')
    InputFormSet = modelformset_factory(
        Commitment,
        form=ProcessInputForm,
        can_delete=True,
        extra=4,
        )
    input_formset = InputFormSet(
        queryset=Commitment.objects.none(),
        data=request.POST or None,
        prefix='input')
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        keep_going = request.POST.get("keep-going")
        just_save = request.POST.get("save")
        if rand_form.is_valid():
            rand = rand_form.save(commit=False)
            rand.created_by = request.user
            rand.order_type = 'rand'
            if process_form.is_valid():
                process_data = process_form.cleaned_data
                process = process_form.save(commit=False)
                process.created_by=request.user
                process.save()
                rand.due_date = process.end_date
                rand.save()
                for form in output_formset.forms:
                    if form.is_valid():
                        output_data = form.cleaned_data
                        qty = output_data["quantity"]
                        agent_type = None
                        if rand.provider:
                            agent_type = rand.provider.agent_type
                        if qty:
                            ct = form.save(commit=False)
                            rt = output_data["resource_type"]
                            rel = ResourceRelationship.objects.get(
                                materiality=rt.materiality,
                                related_to="process",
                                direction="out")
                            ct.relationship = rel
                            ct.event_type = rel.event_type
                            ct.order = rand
                            ct.independent_demand = rand
                            ct.process = process
                            ct.project = process.project
                            ct.from_agent_type=agent_type
                            ct.from_agent=rand.provider
                            ct.to_agent=rand.receiver
                            ct.due_date = process.end_date
                            ct.created_by = request.user
                            ct.save()
                for form in input_formset.forms:
                    if form.is_valid():
                        input_data = form.cleaned_data
                        qty = input_data["quantity"]
                        if qty:
                            ct = form.save(commit=False)
                            rt = input_data["resource_type"]
                            rel = ResourceRelationship.objects.get(
                                materiality=rt.materiality,
                                related_to="process",
                                direction="in")
                            ct.relationship = rel
                            ct.event_type = rel.event_type
                            ct.independent_demand = rand
                            ct.process = process
                            ct.due_date = process.start_date
                            ct.created_by = request.user
                            rt = ct.resource_type
                            ptrt = rt.main_producing_process_type_relationship()
                            if ptrt:
                                ct.project = ptrt.process_type.project
                            ct.save()
                            if ptrt:
                                pt = ptrt.process_type
                                start_date = process.start_date - datetime.timedelta(minutes=pt.estimated_duration)
                                feeder_process = Process(
                                    name=pt.name,
                                    process_type=pt,
                                    project=pt.project,
                                    url=pt.url,
                                    end_date=process.start_date,
                                    start_date=start_date,
                                    created_by=request.user,
                                )
                                feeder_process.save()
                                output_commitment = Commitment(
                                    independent_demand=rand,
                                    event_type=ptrt.relationship.event_type,
                                    relationship=ptrt.relationship,
                                    due_date=process.start_date,
                                    resource_type=rt,
                                    process=feeder_process,
                                    project=pt.project,
                                    quantity=qty,
                                    unit_of_quantity=rt.unit,
                                    created_by=request.user,
                                )
                                output_commitment.save()
                                generate_schedule(feeder_process, rand, request.user)
                return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/order-schedule', rand.id))
    return render_to_response("valueaccounting/create_rand.html", {
        "rand_form": rand_form,
        "process_form": process_form,
        "output_formset": output_formset,
        "input_formset": input_formset,
    }, context_instance=RequestContext(request))

@login_required
def change_rand(request, rand_id):
    #import pdb; pdb.set_trace()
    rand = get_object_or_404(Order, id=rand_id)
    rand_form = RandOrderForm(instance=rand,data=request.POST or None)
    process = None
    for item in rand.producing_commitments():
        if item.process:
            process = item.process
            break
    OutputFormSet = modelformset_factory(
        Commitment,
        form=ProcessOutputForm,
        can_delete=True,
        extra=2,
        )
    InputFormSet = modelformset_factory(
        Commitment,
        form=ProcessInputForm,
        can_delete=True,
        extra=4,
        )
    if process:
        had_process = True
        process_form = ProcessForm(instance=process, data=request.POST or None)
        #output_queryset = process.outgoing_commitments()
        #input_queryset = process.incoming_commitments()
        output_formset = OutputFormSet(
            queryset=process.outgoing_commitments(),
            data=request.POST or None,
            prefix='output')
        input_formset = InputFormSet(
            queryset=process.incoming_commitments(),
            data=request.POST or None,
            prefix='input')
    else:
        had_process = False
        process_form = ProcessForm(data=request.POST or None)
        #output_queryset = Commitment.objects.none()
        #input_queryset = Commitment.objects.none()
        output_formset = OutputFormSet(
            queryset=Commitment.objects.none(),
            data=request.POST or None,
            prefix='output')
        input_formset = InputFormSet(
            queryset=Commitment.objects.none(),
            data=request.POST or None,
            prefix='input')

    #output_formset = OutputFormSet(
    #    queryset=output_queryset,
    #    data=request.POST or None,
    #    prefix='output')
    #input_formset = InputFormSet(
    #    queryset=input_queryset,
    #    data=request.POST or None,
    #    prefix='input')
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        keep_going = request.POST.get("keep-going")
        just_save = request.POST.get("save")
        if rand_form.is_valid():
            rand = rand_form.save(commit=False)
            rand.changed_by = request.user
            if process_form.is_valid():
                process_data = process_form.cleaned_data
                process = process_form.save(commit=False)
                if had_process:
                    process.changed_by=request.user
                else:
                    process.created_by=request.user
                process.save()
                rand.due_date = process.end_date
                rand.save()
                for form in output_formset.forms:
                    if form.is_valid():
                        output_data = form.cleaned_data
                        qty = output_data["quantity"]
                        ct_from_id = output_data["id"]
                        agent_type = None
                        if rand.provider:
                            agent_type = rand.provider.agent_type
                        if qty:
                            ct = form.save(commit=False)
                            if ct_from_id:
                                ct.changed_by = request.user
                                ct.project = process.project
                            else:
                                ct.process = process
                                ct.due_date = process.end_date
                                ct.created_by = request.user
                                rt = output_data["resource_type"]
                                rel = ResourceRelationship.objects.get(
                                    materiality=rt.materiality,
                                    related_to="process",
                                    direction="out")
                                ct.relationship = rel
                                ct.event_type = rel.event_type
                                ct.order = rand
                                ct.independent_demand = rand
                                ct.project = process.project
                                ct.from_agent_type=agent_type
                                ct.from_agent=rand.provider
                                ct.to_agent=rand.receiver
                                ct.created_by = request.user
                            ct.due_date = process.end_date
                            ct.save()
                        elif ct_from_id:
                            ct = form.save()
                            ct.delete()
                for form in input_formset.forms:
                    #import pdb; pdb.set_trace()
                    if form.is_valid():
                        explode = False
                        input_data = form.cleaned_data
                        qty = input_data["quantity"]
                        ct_from_id = input_data["id"]
                        if not qty:
                            if ct_from_id:
                                ct = form.save()
                                trash = []
                                collect_lower_trash(ct, trash)
                                for process in trash:
                                    if process.outgoing_commitments().count() <= 1:
                                        process.delete()
                                ct.delete()
                        else:
                            ct = form.save(commit=False)
                            if ct_from_id:
                                old_ct = Commitment.objects.get(id=ct_from_id.id)
                                old_rt = old_ct.resource_type
                                if ct.resource_type != old_rt:
                                    #import pdb; pdb.set_trace()
                                    old_ct.delete()
                                    for ex_ct in old_rt.producing_commitments():
                                        if rand == ex_ct.independent_demand:
                                            trash = []
                                            collect_trash(ex_ct, trash)
                                            for process in trash:
                                                #todo: feeder process with >1 outputs 
                                                # shd find the correct output to delete
                                                # and keep the others
                                                if process.outgoing_commitments().count() <= 1:
                                                    process.delete()
                                    ptrt = ct.resource_type.main_producing_process_type_relationship()
                                    if ptrt:
                                        ct.project = ptrt.process_type.project
                                    explode = True                                 
                                elif qty != old_ct.quantity:
                                    delta = qty - old_ct.quantity
                                    for pc in ct.resource_type.producing_commitments():
                                        if pc.independent_demand == demand:
                                            propagate_qty_change(pc, delta)                                
                                ct.changed_by = request.user
                                rt = input_data["resource_type"]
                                rel = ResourceRelationship.objects.get(
                                    materiality=rt.materiality,
                                    related_to="process",
                                    direction="in")
                                ct.relationship = rel
                                ct.event_type = rel.event_type
                            else:
                                explode = True
                                rt = input_data["resource_type"]
                                rel = ResourceRelationship.objects.get(
                                    materiality=rt.materiality,
                                    related_to="process",
                                    direction="in")
                                ct.relationship = rel
                                ct.event_type = rel.event_type
                                ct.independent_demand = rand
                                ct.process = process
                                ct.due_date = process.start_date
                                ct.created_by = request.user
                                ptrt = ct.resource_type.main_producing_process_type_relationship()
                                if ptrt:
                                    ct.project = ptrt.process_type.project
                            ct.save()
                            if explode:
                                rt = ct.resource_type
                                ptrt = rt.main_producing_process_type_relationship()
                                if ptrt:
                                    pt = ptrt.process_type
                                    start_date = process.start_date - datetime.timedelta(minutes=pt.estimated_duration)
                                    feeder_process = Process(
                                        name=pt.name,
                                        process_type=pt,
                                        project=pt.project,
                                        url=pt.url,
                                        end_date=process.start_date,
                                        start_date=start_date,
                                        created_by=request.user,
                                    )
                                    feeder_process.save()
                                    output_commitment = Commitment(
                                        independent_demand=rand,
                                        event_type=ptrt.relationship.event_type,
                                        relationship=ptrt.relationship,
                                        due_date=process.start_date,
                                        resource_type=rt,
                                        process=feeder_process,
                                        project=pt.project,
                                        quantity=qty,
                                        unit_of_quantity=rt.unit,
                                        created_by=request.user,
                                    )
                                    output_commitment.save()
                                    generate_schedule(feeder_process, rand, request.user)
                return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/order-schedule', rand.id))
    return render_to_response("valueaccounting/change_rand.html", {
        "rand": rand,
        "rand_form": rand_form,
        "process_form": process_form,
        "output_formset": output_formset,
        "input_formset": input_formset,
    }, context_instance=RequestContext(request))

