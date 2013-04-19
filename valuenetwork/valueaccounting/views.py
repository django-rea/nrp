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
from django.utils.datastructures import SortedDict

from valuenetwork.valueaccounting.models import *
from valuenetwork.valueaccounting.views import *
from valuenetwork.valueaccounting.forms import *
from valuenetwork.valueaccounting.utils import *

def get_agent(request):
    #import pdb; pdb.set_trace()
    agent = None
    nick = request.user.username
    if nick:
        try:
            agent = EconomicAgent.objects.get(nick=nick.capitalize)
        except EconomicAgent.DoesNotExist:
            try:
                agent = EconomicAgent.objects.get(nick=nick)
            except EconomicAgent.DoesNotExist:
                pass
    return agent

def home(request):
    work_to_do = Commitment.objects.unfinished().filter(
            from_agent=None, 
            resource_type__materiality="work")
    reqs = Commitment.objects.unfinished().filter(
        resource_type__materiality="material",
        relationship__direction="in").order_by("resource_type__name")
    stuff = SortedDict()
    for req in reqs:
        if req.quantity_to_buy():
            if req.resource_type not in stuff:
                stuff[req.resource_type] = Decimal("0")
            stuff[req.resource_type] += req.quantity_to_buy()
    treqs = Commitment.objects.unfinished().filter(
        resource_type__materiality="tool",
        relationship__direction="in").order_by("resource_type__name")
    for req in treqs:
        if req.quantity_to_buy():
            if req.resource_type not in stuff:
                stuff[req.resource_type] = req.quantity_to_buy()
    value_creations = Commitment.objects.unfinished().filter(
        relationship__direction="out")
    return render_to_response("homepage.html", {
        "work_to_do": work_to_do,
        "stuff_to_buy": stuff,
        "value_creations": value_creations,
        "photo_size": (128, 128),
    }, context_instance=RequestContext(request))

def projects(request):
    roots = Project.objects.filter(parent=None)
    agent = get_agent(request)
    
    return render_to_response("valueaccounting/projects.html", {
        "roots": roots,
        "agent": agent,
    }, context_instance=RequestContext(request))

@login_required
def sessions(request):
    if not request.user.is_superuser:
        return render_to_response('valueaccounting/no_permission.html')
    from django.contrib.sessions.models import Session
    sessions = Session.objects.all().order_by('-expire_date')[0:20]
    for session in sessions:
        data = session.get_decoded()
        try:
            session.user = User.objects.get(id=data['_auth_user_id'])
        except:
            session.user = "guest"
    selected_session = None
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        spk = request.POST.get("session")
        if spk:
            try:
                ss = Session.objects.get(pk=spk)
                selected_session = ss
                data = selected_session.get_decoded()
                try:
                    selected_session.user = User.objects.get(id=data['_auth_user_id'])
                except:
                    selected_session.user = "guest"
            except Session.DoesNotExist:
                pass
            
    return render_to_response("valueaccounting/sessions.html", {
        "sessions": sessions,
        "selected_session": selected_session,
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

def inventory(request):
    #TODO: resource types don't have to have categories, for now assuming they all will
    resources = EconomicResource.objects.select_related().filter(quantity__gt=0).order_by('resource_type__category', 'resource_type')
    categories = Category.objects.all()
    select_all = True
    selected_cats = "all"
    if request.method == "POST":
        selected_cats = request.POST["categories"]
        cats = selected_cats.split(",")
        if cats[0] == "all":
            select_all = True
            resources = EconomicResource.objects.select_related().filter(quantity__gt=0).order_by('resource_type__category', 'resource_type')
        else:
            select_all = False
            resources = EconomicResource.objects.select_related().filter(quantity__gt=0, resource_type__category__name__in=cats).order_by('resource_type__category', 'resource_type')
    return render_to_response("valueaccounting/inventory.html", {
        "resources": resources,
        "categories": categories,
        "select_all": select_all,
        "selected_cats": selected_cats,
        "photo_size": (128, 128),
    }, context_instance=RequestContext(request))

def all_contributions(request):
    event_list = EconomicEvent.objects.filter(is_contribution=True)
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
    
    return render_to_response("valueaccounting/all_contributions.html", {
        "events": events,
    }, context_instance=RequestContext(request))

def contributions(request, project_id):
    #import pdb; pdb.set_trace()
    project = get_object_or_404(Project, pk=project_id)
    event_list = project.contribution_events()
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

def project_wip(request, project_id):
    #import pdb; pdb.set_trace()
    project = get_object_or_404(Project, pk=project_id)
    process_list = project.wip()
    paginator = Paginator(process_list, 25)

    page = request.GET.get('page')
    try:
        processes = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        processes = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        processes = paginator.page(paginator.num_pages)
    
    return render_to_response("valueaccounting/project_wip.html", {
        "project": project,
        "processes": processes,
    }, context_instance=RequestContext(request))

def contribution_history(request, agent_id):
    #import pdb; pdb.set_trace()
    agent = get_object_or_404(EconomicAgent, pk=agent_id)
    event_list = agent.contributions()
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

@login_required
def unscheduled_time_contributions(request):
    member = get_agent(request)
    if not member:
        return HttpResponseRedirect('/%s/'
            % ('accounting/work'))
    TimeFormSet = modelformset_factory(
        EconomicEvent,
        form=CasualTimeContributionForm,
        can_delete=False,
        extra=8,
        max_num=8,
        )
    time_formset = TimeFormSet(
        queryset=EconomicEvent.objects.none(),
        data=request.POST or None)
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        keep_going = request.POST.get("keep-going")
        just_save = request.POST.get("save")
        if time_formset.is_valid():
            events = time_formset.save(commit=False)
            rel = ResourceRelationship.objects.get(
                materiality="work",
                related_to="process",
                direction="in")
            event_type=rel.event_type
            unit = Unit.objects.filter(
                unit_type="time",
                name__icontains="Hours")[0]
            for event in events:
                if event.event_date and event.quantity:
                    event.from_agent=member
                    event.is_contribution=True
                    event.event_type=event_type
                    event.unit_of_quantity=unit
                    event.created_by=request.user
                    event.save()
            if keep_going:
                return HttpResponseRedirect('/%s/'
                    % ('accounting/unscheduled-time'))
            else:
                return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/contributionhistory', member.id))
    
    return render_to_response("valueaccounting/unscheduled_time_contributions.html", {
        "member": member,
        "time_formset": time_formset,
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
    pcs = order.producing_commitments()
    sked = []
    reqs = []
    work = []
    tools = []
    if pcs:
        visited_resources = set()
        for ct in pcs:
            visited_resources.add(ct.resource_type)
            schedule_commitment(ct, sked, reqs, work, tools, visited_resources, 0)
        return render_to_response('valueaccounting/order_delete_confirmation.html', {
            "order": order,
            "sked": sked,
            "reqs": reqs,
            "work": work,
            "tools": tools,
        }, context_instance=RequestContext(request))
    else:
        commitments = Commitment.objects.filter(independent_demand=order)
        if commitments:
            for ct in commitments:
                sked.append(ct)
                if ct.process not in sked:
                    sked.append(ct.process)
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
        visited_resources = set()
        pcs = order.producing_commitments()
        if pcs:
            for ct in pcs:
                visited_resources.add(ct.resource_type)
                collect_trash(ct, trash, visited_resources)
                order.delete()
                for item in trash:
                    item.delete()
        else:
            commitments = Commitment.objects.filter(independent_demand=order)
            if commitments:
                #import pdb; pdb.set_trace()
                processes = []
                for ct in commitments:
                    if ct.process:
                        processes.append(ct.process)
                    for event in ct.fulfillment_events.all():
                        event.commitment = None
                        event.save()
                    ct.delete()
                for process in processes:
                    process.delete()
            order.delete()
        next = request.POST.get("next")
        if next:
            return HttpResponseRedirect(next)
        else:
            return HttpResponseRedirect('/%s/'
                % ('accounting/demand'))

def collect_trash(commitment, trash, visited_resources):
    order = commitment.independent_demand
    process = commitment.process
    trash.append(process)
    for inp in process.incoming_commitments():
        resource_type = inp.resource_type
        if resource_type not in visited_resources:
            visited_resources.add(resource_type)
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
                rt = rts[0]
                feature.product=rt
                rel = ResourceRelationship.objects.get(
                    materiality=rt.materiality,
                    related_to="process",
                    direction="in")
                feature.relationship = rel
            else:
                #todo: when will we get here? It's a hack.
                rel = ResourceRelationship.objects.get(
                    materiality="material",
                    related_to="process",
                    direction="in")
                feature.relationship = rel
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
    #import pdb; pdb.set_trace()
    producers = [p for p in ProcessType.objects.all() if p.produced_resource_types()]
    nodes, edges = project_graph(producers)
    return render_to_response("valueaccounting/network.html", {
        "photo_size": (128, 128),
        "nodes": nodes,
        "edges": edges,
    }, context_instance=RequestContext(request))

def timeline(request):
    timeline_date = datetime.date.today().strftime("%b %e %Y 00:00:00 GMT-0600")
    unassigned = Commitment.objects.unfinished().filter(
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
    rts = EconomicResourceType.objects.process_outputs().filter(category__in=cats)
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
                        if pt:
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
                            generate_schedule(process, order, request.user)
                        else:
                            rel = ResourceRelationship.objects.get(
                                materiality=rt.materiality,
                                related_to="process",
                                direction="out")
                            commitment = Commitment(
                                order=order,
                                independent_demand=order,
                                event_type=rel.event_type,
                                relationship=rel,
                                due_date=order.due_date,
                                from_agent_type=order.provider.agent_type,
                                from_agent=order.provider,
                                to_agent=order.receiver,
                                resource_type=rt,
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
                                if process_type:
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
                                else:
                                    commitment = Commitment(
                                        independent_demand=order,
                                        event_type=feature.relationship.event_type,
                                        relationship=feature.relationship,
                                        due_date=process.start_date,
                                        to_agent=order.provider,
                                        resource_type=component,
                                        quantity=qty * feature.quantity,
                                        unit_of_quantity=component.unit,
                                        created_by=request.user,
                                    )
                                    commitment.save()
                        
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
        visited_resources,
        depth):
    #import pdb; pdb.set_trace()
    order = commitment.independent_demand
    commitment.depth = depth * 2
    schedule.append(commitment)
    process = commitment.process
    if process:
        process.depth = depth * 2
        schedule.append(process)
        #import pdb; pdb.set_trace()
        for inp in process.schedule_requirements():
            inp.depth = depth * 2
            schedule.append(inp)
            resource_type = inp.resource_type
            if resource_type not in visited_resources:
                visited_resources.add(resource_type)
                pcs = resource_type.producing_commitments()
                if pcs:
                    for pc in pcs:
                        if pc.independent_demand == order:
                            schedule_commitment(pc, schedule, reqs, work, tools, visited_resources, depth+1)
                elif inp.independent_demand == order:
                    #if resource_type.materiality == 'material':
                    #    reqs.append(inp)
                    #elif resource_type.materiality == 'work':
                    #    work.append(inp)
                    #elif resource_type.materiality == 'tool':
                    #    tools.append(inp)
                    reqs.append(inp)
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
    visited_resources = set()
    #import pdb; pdb.set_trace()
    pcs = order.producing_commitments()
    error_message = ""
    if pcs:
        for ct in pcs:
            visited_resources.add(ct.resource_type)
            schedule_commitment(ct, sked, reqs, work, tools, visited_resources, 0)
    else:
        error_message = "An R&D order needs an output to find its schedule"
    return render_to_response("valueaccounting/order_schedule.html", {
        "order": order,
        "sked": sked,
        "reqs": reqs,
        "work": work,
        "tools": tools,
        "error_message": error_message,
    }, context_instance=RequestContext(request))

def demand(request):
    orders = Order.objects.filter(order_type='customer')
    rands = Order.objects.filter(order_type='rand')
    return render_to_response("valueaccounting/demand.html", {
        "orders": orders,
        "rands": rands,
    }, context_instance=RequestContext(request))

def supply(request):
    mreqs = []
    mrqs = Commitment.objects.unfinished().filter(
        resource_type__materiality="material",
        relationship__direction="in").order_by("resource_type__name")
    suppliers = SortedDict()
    for commitment in mrqs:
        if not commitment.resource_type.producing_commitments():
            if not commitment.fulfilling_events():    
                mreqs.append(commitment)
                sources = commitment.resource_type.producing_agent_relationships().order_by("resource_type__name")
                for source in sources:
                    agent = source.agent
                    if agent not in suppliers:
                        suppliers[agent] = SortedDict()
                    if source not in suppliers[agent]:
                        suppliers[agent][source] = []
                    suppliers[agent][source].append(commitment) 
    treqs = []
    trqs = Commitment.objects.unfinished().filter(
        resource_type__materiality="tool",
        relationship__direction="in").order_by("resource_type__name")
    for commitment in trqs:
        if not commitment.resource_type.producing_commitments():
            if not commitment.fulfilling_events():    
                treqs.append(commitment)
                sources = commitment.resource_type.producing_agent_relationships().order_by("resource_type__name")
                for source in sources:
                    agent = source.agent
                    if agent not in suppliers:
                        suppliers[agent] = SortedDict()
                    if source not in suppliers[agent]:
                        suppliers[agent][source] = []
                    suppliers[agent][source].append(commitment)  
    return render_to_response("valueaccounting/supply.html", {
        "mreqs": mreqs,
        "treqs": treqs,
        "suppliers": suppliers,
    }, context_instance=RequestContext(request))

def work_old(request):
    my_work = []
    my_skillz = []
    other_wip = []
    agent = get_agent(request)
    if agent:
        my_work = Commitment.objects.unfinished().filter(
            resource_type__materiality="work",
            from_agent=agent)
        skill_ids = agent.resource_types.values_list('resource_type__id', flat=True)
        my_skillz = Commitment.objects.unfinished().filter(
            from_agent=None, 
            resource_type__materiality="work",
            resource_type__id__in=skill_ids)
        other_unassigned = Commitment.objects.unfinished().filter(
            from_agent=None, 
            resource_type__materiality="work").exclude(resource_type__id__in=skill_ids)
        other_wip = Commitment.objects.unfinished().filter(
            resource_type__materiality="work").exclude(from_agent=None).exclude(from_agent=agent)
    else:
        other_unassigned = Commitment.objects.unfinished().filter(
            from_agent=None, 
            resource_type__materiality="work")
    start = datetime.date.today()
    end = start + datetime.timedelta(days=7)
    init = {"start_date": start, "end_date": end}
    date_form = DateSelectionForm(initial=init)
    return render_to_response("valueaccounting/work.html", {
        "agent": agent,
        "my_work": my_work,
        "my_skillz": my_skillz,
        "other_unassigned": other_unassigned,
        "other_wip": other_wip,
        "date_form": date_form,
    }, context_instance=RequestContext(request))

def assemble_schedule(start, end):
    processes = Process.objects.unfinished().filter(
        Q(start_date__range=(start, end)) | Q(end_date__range=(start, end)))
    processes = processes.order_by("project__name")
    projects = SortedDict()
    for proc in processes:
        if proc.project not in projects:
            projects[proc.project] = []
        projects[proc.project].append(proc)
    return projects

def work(request):
    agent = get_agent(request)
    start = datetime.date.today()
    #start = start - datetime.timedelta(days=7)
    end = start + datetime.timedelta(days=7)
    projects = assemble_schedule(start, end)   
    init = {"start_date": start, "end_date": end}
    date_form = DateSelectionForm(initial=init, data=request.POST or None)
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        if date_form.is_valid():
            dates = date_form.cleaned_data
            start = dates["start_date"]
            end = dates["end_date"]
            projects = assemble_schedule(start, end) 
    return render_to_response("valueaccounting/work.html", {
        "agent": agent,
        "projects": projects,
        "date_form": date_form,
    }, context_instance=RequestContext(request))

def start(request):
    my_work = []
    my_skillz = []
    other_wip = []
    scores = []
    agent = get_agent(request)
    if agent:
        my_work = Commitment.objects.unfinished().filter(
            resource_type__materiality="work",
            from_agent=agent)
        skill_ids = agent.resource_types.values_list('resource_type__id', flat=True)
        my_skillz = Commitment.objects.unfinished().filter(
            from_agent=None, 
            resource_type__materiality="work",
            resource_type__id__in=skill_ids)
        other_unassigned = Commitment.objects.unfinished().filter(
            from_agent=None, 
            resource_type__materiality="work").exclude(resource_type__id__in=skill_ids)
        scores = agent.resource_types.all()
        
    else:
        other_unassigned = Commitment.objects.unfinished().filter(
            from_agent=None, 
            resource_type__materiality="work")

    contributions = EconomicEvent.objects.filter(is_contribution=True)
    agents = {}
    for c in contributions:
        if c.from_agent not in agents:
            agents[c.from_agent] = Decimal("0")
        agents[c.from_agent] += c.quantity
    member_hours = []
    for key, value in agents.iteritems():
        member_hours.append((key, value))
    member_hours.sort(lambda x, y: cmp(y[1], x[1]))

    return render_to_response("valueaccounting/start.html", {
        "agent": agent,
        "my_work": my_work,
        "my_skillz": my_skillz,
        "other_unassigned": other_unassigned,
        "scores": scores,
        "member_hours": member_hours,
    }, context_instance=RequestContext(request))


def commit_to_task(request, commitment_id):
    if request.method == "POST":
        ct = get_object_or_404(Commitment, id=commitment_id)
        process = ct.process
        agent = get_agent(request)
        prefix = ct.form_prefix()
        form = CommitmentForm(data=request.POST, prefix=prefix)
        next = request.POST.get("next")
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
            if request.POST.get("start"):
                return HttpResponseRedirect('/%s/%s/'
                % ('accounting/work-commitment', ct.id))
        
        return HttpResponseRedirect(next)

def create_labnotes_context(
        request, 
        commitment, 
        was_running=0,
        was_retrying=0):
    event = None
    duration = 0
    description = ""
    prev = ""
    today = datetime.date.today()
    events = commitment.fulfillment_events.filter(event_date=today)
    if events:
        event = events[events.count() - 1]
        init = {
            "work_done": commitment.finished,
            "process_done": commitment.process.finished,
        }
        wb_form = WorkbookForm(instance=event, initial=init)
        duration = event.quantity * 60     
    else:
        init = {
            "description": commitment.description,
            "work_done": commitment.finished,
            "process_done": commitment.process.finished,
        }
        wb_form = WorkbookForm(initial=init)
    prev_events = commitment.fulfillment_events.filter(event_date__lt=today)
    #import pdb; pdb.set_trace()
    if prev_events:
        prev_dur = sum(prev.quantity for prev in prev_events)
        unit = ""
        if commitment.unit_of_quantity:
            unit = commitment.unit_of_quantity.name
        prev = " ".join([str(prev_dur), unit])
    others_working = []
    other_work_reqs = []
    #import pdb; pdb.set_trace()
    process = commitment.process
    wrqs = process.work_requirements()
    if wrqs.count() > 1:
        for wrq in wrqs:
            if wrq.from_agent != commitment.from_agent:
                if wrq.from_agent:
                    wrq.has_labnotes = wrq.agent_has_labnotes(wrq.from_agent)
                    others_working.append(wrq)
                else:
                    other_work_reqs.append(wrq)
    failure_form = FailedOutputForm()
    add_output_form = ProcessOutputForm(prefix='output')
    add_citation_form = ProcessCitationForm(prefix='citation')
    add_input_form = ProcessInputForm(prefix='input')
    cited_ids = [c.resource.id for c in process.citations()]
    return {
        "commitment": commitment,
        "process": process,
        "wb_form": wb_form,
        "others_working": others_working,
        "other_work_reqs": other_work_reqs,
        "today": today,
        "failure_form": failure_form,
        "add_output_form": add_output_form,
        "add_citation_form": add_citation_form,
        "add_input_form": add_input_form,
        "duration": duration,
        "prev": prev,
        "was_running": was_running,
        "was_retrying": was_retrying,
        "event": event,
        "cited_ids": cited_ids,
    }

def new_process_output(request, commitment_id):
    commitment = get_object_or_404(Commitment, pk=commitment_id)
    process = commitment.process
    was_running = request.POST["wasRunning"]
    was_retrying = request.POST["wasRetrying"]
    event_date = request.POST.get("outputDate")
    #import pdb; pdb.set_trace()
    event = None
    events = None
    event_id=0
    if event_date:
        event_date = datetime.datetime.strptime(event_date, '%Y-%m-%d').date()
        events = commitment.fulfillment_events.filter(event_date=event_date)
    if events:
        event = events[events.count() - 1]
        event_id = event.id
    reload = request.POST["reload"]
    if request.method == "POST":
        form = ProcessOutputForm(data=request.POST, prefix='output')
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
                ct.independent_demand = commitment.independent_demand
                ct.due_date = process.end_date
                ct.created_by = request.user
                ct.save()
                if process.name == "Make something":
                    process.name = " ".join([
                                "Make",
                                ct.resource_type.name,
                            ])
                    process.save()
    if reload == 'pastwork':
        return HttpResponseRedirect('/%s/%s/%s/%s/%s/'
            % ('accounting/pastwork-reload', commitment.id, event_id, was_running, was_retrying))
    else:
        return HttpResponseRedirect('/%s/%s/%s/%s/'
            % ('accounting/labnotes-reload', commitment.id, was_running, was_retrying))

def new_process_input(request, commitment_id):
    commitment = get_object_or_404(Commitment, pk=commitment_id)
    was_running = request.POST["wasRunning"] or 0
    was_retrying = request.POST["wasRetrying"] or 0
    #import pdb; pdb.set_trace()
    event_date = request.POST.get("inputDate")
    event = None
    events = None
    event_id=0
    if event_date:
        event_date = datetime.datetime.strptime(event_date, '%Y-%m-%d').date()
        events = commitment.fulfillment_events.filter(event_date=event_date)
    if events:
        event = events[events.count() - 1]
        event_id = event.id
    reload = request.POST["reload"]
    if request.method == "POST":
        form = ProcessInputForm(data=request.POST, prefix='input')
        if form.is_valid():
            input_data = form.cleaned_data
            qty = input_data["quantity"]
            if qty:
                process = commitment.process
                demand = process.independent_demand()
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
                ptrt = ct.resource_type.main_producing_process_type_relationship()
                if ptrt:
                    ct.project = ptrt.process_type.project
                ct.save()
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
                
    if reload == 'pastwork':
        return HttpResponseRedirect('/%s/%s/%s/%s/%s/'
            % ('accounting/pastwork-reload', commitment.id, event_id, was_running, was_retrying))
    else:
        return HttpResponseRedirect('/%s/%s/%s/%s/'
            % ('accounting/labnotes-reload', commitment.id, was_running, was_retrying))

def new_process_citation(request, commitment_id):
    commitment = get_object_or_404(Commitment, pk=commitment_id)
    was_running = request.POST["wasRunning"] or 0
    was_retrying = request.POST["wasRetrying"] or 0
    #import pdb; pdb.set_trace()
    event_date = request.POST.get("citationDate")
    event = None
    events = None
    event_id=0
    if event_date:
        event_date = datetime.datetime.strptime(event_date, '%Y-%m-%d').date()
        events = commitment.fulfillment_events.filter(event_date=event_date)
    if events:
        event = events[events.count() - 1]
        event_id = event.id
    reload = request.POST["reload"]
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        form = ProcessCitationForm(data=request.POST, prefix='citation')
        if form.is_valid():
            input_data = form.cleaned_data
            process = commitment.process
            demand = process.independent_demand()
            quantity = Decimal("1")
            rt_id = input_data["resource_type"]
            rt = EconomicResourceType.objects.get(id=rt_id)
            rel = ResourceRelationship.objects.get(
                materiality=rt.materiality,
                related_to="process",
                direction="cite")
            agent = get_agent(request)
            ct = Commitment(
                process=process,
                from_agent=agent,
                independent_demand=demand,
                event_type=rel.event_type,
                relationship=rel,
                due_date=process.start_date,
                resource_type=rt,
                project=process.project,
                quantity=quantity,
                unit_of_quantity=rt.unit,
                created_by=request.user,
            )
            ct.save()
                
    if reload == 'pastwork':
        return HttpResponseRedirect('/%s/%s/%s/%s/%s/'
            % ('accounting/pastwork-reload', commitment.id, event_id, was_running, was_retrying))
    else:
        return HttpResponseRedirect('/%s/%s/%s/%s/'
            % ('accounting/labnotes-reload', commitment.id, was_running, was_retrying))

def delete_commitment(request, commitment_id, labnotes_id):
    commitment = get_object_or_404(Commitment, pk=commitment_id)
    ct = get_object_or_404(Commitment, pk=labnotes_id)
    #import pdb; pdb.set_trace()
    commitment.delete()
    was_running = request.POST["wasRunning"] or 0
    was_retrying = request.POST["wasRetrying"] or 0
    reload = request.POST["reload"]
    event_date = request.POST.get("eventDate")
    event = None
    events = None
    event_id=0
    if event_date:
        event_date = datetime.datetime.strptime(event_date, '%Y-%m-%d').date()
        events = ct.fulfillment_events.filter(event_date=event_date)
    if events:
        event = events[events.count() - 1]
        event_id = event.id
    if reload == 'pastwork':
        return HttpResponseRedirect('/%s/%s/%s/%s/%s/'
            % ('accounting/pastwork-reload', labnotes_id, event_id, was_running, was_retrying))
    else:
        return HttpResponseRedirect('/%s/%s/%s/%s/'
            % ('accounting/labnotes-reload', labnotes_id, was_running, was_retrying))

def work_done(request):
    #import pdb; pdb.set_trace()
    commitment_id = int(request.POST.get("commitmentId"))
    done = int(request.POST.get("done"))
    commitment = get_object_or_404(Commitment, pk=commitment_id)
    if done:
        if not commitment.finished:
            commitment.finished = True
            commitment.save()
    else:
        if commitment.finished:
            commitment.finished = False
            commitment.save()

    return HttpResponse("Ok", mimetype="text/plain")

   
def process_done(request):
    #import pdb; pdb.set_trace()
    process_id = int(request.POST.get("processId"))
    commitment_id = int(request.POST.get("commitmentId"))
    done = int(request.POST.get("done"))
    process = get_object_or_404(Process, pk=process_id)
    if process.work_requirements().count() == 1:
        commitment = get_object_or_404(Commitment, pk=commitment_id)
        if done:
            if not commitment.finished:
                commitment.finished = True
                commitment.save()
        else:
            if commitment.finished:
                commitment.finished = False
                commitment.save()
    if done:
        if not process.finished:
            process.finished = True
            process.save()
    else:
        if process.finished:
            process.finished = False
            process.save()

    return HttpResponse("Ok", mimetype="text/plain")
  

def labnotes_reload(
        request, 
        commitment_id, 
        was_running=0,
        was_retrying=0):
    ct = get_object_or_404(Commitment, id=commitment_id)
    #import pdb; pdb.set_trace()
    template_params = create_labnotes_context(
        request, 
        ct, 
        was_running,
        was_retrying,
    )
    return render_to_response("valueaccounting/workbook.html",
        template_params,
        context_instance=RequestContext(request))

@login_required
def work_commitment(
        request, 
        commitment_id):
    ct = get_object_or_404(Commitment, id=commitment_id)
    #import pdb; pdb.set_trace()
    agent = get_agent(request)
    if not request.user.is_superuser:
        if agent != ct.from_agent:
            return render_to_response('valueaccounting/no_permission.html')
    template_params = create_labnotes_context(
        request, 
        ct, 
    )
    event = template_params["event"]
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        today = datetime.date.today()
        wb_form = WorkbookForm(request.POST)
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
                event.is_contribution = True
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
            return HttpResponseRedirect('/%s/%s/'
            % ('accounting/labnote', ct.id))
    return render_to_response("valueaccounting/workbook.html",
        template_params,
        context_instance=RequestContext(request))

def create_past_work_context(
        request, 
        commitment, 
        was_running=0,
        was_retrying=0,
        event=None):
    duration = 0
    description = ""
    prev = ""
    event_date=None
    #import pdb; pdb.set_trace()
    if event:
        init = {
                "work_done": commitment.finished,
                "process_done": commitment.process.finished,
            }
        wb_form = PastWorkForm(instance=event, initial=init)
        duration = event.quantity * 60 
        event_date=event.event_date
    else:
        init = {
            "description": commitment.description,
            "work_done": commitment.finished,
            "process_done": commitment.process.finished,
        }
        wb_form = PastWorkForm(initial=init)
    if event_date:
        prev_events = commitment.fulfillment_events.filter(event_date__lt=event_date)
    else:
        prev_events = commitment.fulfillment_events.all()
    if prev_events:
        prev_dur = sum(prev.quantity for prev in prev_events)
        unit = ""
        if commitment.unit_of_quantity:
            unit = commitment.unit_of_quantity.name
        prev = " ".join([str(prev_dur), unit])
    others_working = []
    other_work_reqs = []
    #import pdb; pdb.set_trace()
    process = commitment.process
    wrqs = process.work_requirements()
    if wrqs.count() > 1:
        for wrq in wrqs:
            if wrq.from_agent != commitment.from_agent:
                if wrq.from_agent:
                    wrq.has_labnotes = wrq.agent_has_labnotes(wrq.from_agent)
                    others_working.append(wrq)
                else:
                    other_work_reqs.append(wrq)
    failure_form = FailedOutputForm()
    add_output_form = ProcessOutputForm(prefix='output')
    add_citation_form = ProcessCitationForm(prefix='citation')
    add_input_form = ProcessInputForm(prefix='input')
    cited_ids = [c.resource.id for c in process.citations()]
    return {
        "commitment": commitment,
        "process": process,
        "wb_form": wb_form,
        "others_working": others_working,
        "other_work_reqs": other_work_reqs,
        "failure_form": failure_form,
        "add_output_form": add_output_form,
        "add_citation_form": add_citation_form,
        "add_input_form": add_input_form,
        "duration": duration,
        "prev": prev,
        "was_running": was_running,
        "was_retrying": was_retrying,
        "event": event,
        "event_date": event_date,
        "cited_ids": cited_ids,
    }

@login_required
def pastwork_reload(
        request, 
        commitment_id, 
        event_id,
        was_running=0,
        was_retrying=0,
        ):
    ct = get_object_or_404(Commitment, id=commitment_id)
    agent = get_agent(request)
    if agent != ct.from_agent:
        return render_to_response('valueaccounting/no_permission.html')
    #import pdb; pdb.set_trace()
    event=None
    event_id = int(event_id)
    if event_id:
        event = get_object_or_404(EconomicEvent, id=event_id)
    template_params = create_past_work_context(
        request, 
        ct, 
        was_running,
        was_retrying,
        event,
    )
    if request.method == "POST":
        return HttpResponseRedirect('/%s/%s/'
            % ('accounting/labnote', ct.id))
    return render_to_response("valueaccounting/log_past_work.html",
        template_params,
        context_instance=RequestContext(request))

@login_required
def log_past_work(
        request, 
        commitment_id):
    ct = get_object_or_404(Commitment, id=commitment_id)
    #import pdb; pdb.set_trace()
    agent = get_agent(request)
    if not request.user.is_superuser:
        if agent != ct.from_agent:
            return render_to_response('valueaccounting/no_permission.html')
    template_params = create_past_work_context(
        request, 
        ct,
    )
    event = template_params["event"]
    if request.method == "POST":
        return HttpResponseRedirect('/%s/%s/'
            % ('accounting/labnote', ct.id))
    return render_to_response("valueaccounting/log_past_work.html",
        template_params,
        context_instance=RequestContext(request))

@login_required
def save_labnotes(request, commitment_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        ct = get_object_or_404(Commitment, id=commitment_id)
        event = None
        event_date = request.POST.get("event_date")
        if event_date:
            event_date = datetime.datetime.strptime(event_date, '%Y-%m-%d').date()
        else:
            event_date = datetime.date.today()
        events = ct.fulfillment_events.filter(event_date=event_date)
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
                if not event.event_date:
                    event.event_date = event_date
                event.commitment = ct
                event.is_contribution = True
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
                    process.started = event_date
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

@login_required
def save_past_work(request, commitment_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        ct = get_object_or_404(Commitment, id=commitment_id)
        event_date = request.POST.get("eventDate")
        if event_date:
            event_date = datetime.datetime.strptime(event_date, '%Y-%m-%d').date()
        events = ct.fulfillment_events.filter(event_date=event_date)
        if events:
            event = events[events.count() - 1]
            form = PastWorkForm(instance=event, data=request.POST)
        else:
            form = PastWorkForm(data=request.POST)
        if form.is_valid():
            data = form.cleaned_data
            event_id = data.get("id")
            if event_id:
                event = form.save(commit=False)
                event.event_date = event_date
                event.changed_by = request.user
            else:
                event = form.save(commit=False)
                event.event_date = event_date
                event.commitment = ct
                event.is_contribution = True
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
                    process.started = event_date
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
    cited_ids = [c.resource.id for c in process.citations()]
    return render_to_response("valueaccounting/process.html", {
        "process": process,
        "labnotes": labnotes,
        "cited_ids": cited_ids,
    }, context_instance=RequestContext(request))

def resource(request, resource_id):
    resource = get_object_or_404(EconomicResource, id=resource_id)
    return render_to_response("valueaccounting/resource.html", {
        "resource": resource,
        "photo_size": (128, 128),
    }, context_instance=RequestContext(request))

def get_labnote_context(commitment, request_agent):
    author = False
    agent = commitment.from_agent
    process = commitment.process
    if request_agent == agent:
        author = True
    work_events = commitment.fulfilling_events()
    outputs = process.outputs_from_agent(agent)
    failures = process.failures_from_agent(agent)
    inputs = process.inputs_used_by_agent(agent)
    citations = process.citations_by_agent(agent)
    return {
        "commitment": commitment,
        "author": author,
        "process": process,
        "work_events": work_events,
        "outputs": outputs,
        "failures": failures,
        "inputs": inputs,
        "citations": citations,
    }
    

def labnotes(request, process_id):
    process = get_object_or_404(Process, id=process_id)
    agent = get_agent(request)
    work_commitments = process.work_requirements()
    #import pdb; pdb.set_trace()
    if work_commitments.count() == 1:
        ct = work_commitments[0]
        template_params = get_labnote_context(ct, agent)
        return render_to_response("valueaccounting/labnote.html",
            template_params,
            context_instance=RequestContext(request))
    else:
        return render_to_response("valueaccounting/labnotes.html", {
            "process": process,
            "agent": agent,
        }, context_instance=RequestContext(request))

def labnote(request, commitment_id):
    ct = get_object_or_404(Commitment, id=commitment_id)
    request_agent = get_agent(request)
    template_params = get_labnote_context(ct, request_agent)
    return render_to_response("valueaccounting/labnote.html",
        template_params,
        context_instance=RequestContext(request))

def production_event_for_commitment(request):
    id = request.POST.get("id")
    quantity = request.POST.get("quantity")
    event_date = request.POST.get("eventDate")
    #import pdb; pdb.set_trace()
    if event_date:
        event_date = datetime.datetime.strptime(event_date, '%Y-%m-%d').date()
    else:
        event_date = datetime.date.today()
    ct = get_object_or_404(Commitment, pk=id)
    agent = get_agent(request)
    #import pdb; pdb.set_trace()
    quantity = Decimal(quantity)
    event = None
    events = ct.fulfillment_events.all()
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
            created_date = event_date,
            quantity = quantity,
            unit_of_quantity = ct.unit_of_quantity,
            created_by=request.user,
        )
        resource.save()
        event = EconomicEvent(
            resource = resource,
            commitment = ct,
            event_date = event_date,
            event_type = ct.event_type,
            from_agent = agent,
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

def resource_event_for_commitment(request, commitment_id):
    #todo: bug: resource_event_for_commitment didn't return an HttpResponse object.
    id = request.POST.get("itemId")
    event_date = request.POST.get("eventDate")
    #import pdb; pdb.set_trace()
    if event_date:
        event_date = datetime.datetime.strptime(event_date, '%Y-%m-%d').date()
    else:
        event_date = datetime.date.today()
    #import pdb; pdb.set_trace()
    ct = get_object_or_404(Commitment, pk=id)
    event = None
    events = ct.fulfillment_events.all()
    prefix = ct.form_prefix()
    data = unicode('0')
    if events:
        event = events[events.count() - 1]
        form = EconomicResourceForm(prefix=prefix, data=request.POST, instance=event.resource)
    else:
        form = EconomicResourceForm(prefix=prefix, data=request.POST)
    if form.is_valid():
        resource_data = form.cleaned_data
        quality = resource_data["quality"] or Decimal("0")
        agent = get_agent(request)
        if event:
            resource = form.save(commit=False)
            if event.quantity != resource.quantity:
                event.quantity = resource.quantity
                event.changed_by = request.user
                event.save()
            resource.changed_by=request.user
            resource.save()
        else:
            resource = form.save(commit=False)
            resource.quality = quality
            resource.resource_type = ct.resource_type
            resource.created_by=request.user
            resource.save()
            event = EconomicEvent(
                resource = resource,
                commitment = ct,
                event_date = event_date,
                event_type = ct.event_type,
                from_agent = agent,
                resource_type = ct.resource_type,
                process = ct.process,
                project = ct.project,
                quantity = resource.quantity,
                unit_of_quantity = ct.unit_of_quantity,
                quality = resource.quality,
                created_by = request.user,
                changed_by = request.user,
            )
            event.save()
        data = unicode(resource.quantity)
    return HttpResponse(data, mimetype="text/plain")


#todo: how to handle splits?
def consumption_event_for_commitment(request):
    id = request.POST.get("id")
    resource_id = request.POST.get("resourceId")
    quantity = request.POST.get("quantity")
    event_date = request.POST.get("eventDate")
    if event_date:
        event_date = datetime.datetime.strptime(event_date, '%Y-%m-%d').date()
    else:
        event_date = datetime.date.today()
    #import pdb; pdb.set_trace()
    ct = get_object_or_404(Commitment, pk=id)
    resource = get_object_or_404(EconomicResource, pk=resource_id)
    agent = get_agent(request)
    #import pdb; pdb.set_trace()
    quantity = Decimal(quantity)
    event = None
    events = ct.fulfillment_events.filter(resource=resource)
    if events:
        event = events[events.count() - 1]
    if event:
        if event.quantity != quantity:
            delta = event.quantity - quantity
            event.quantity = quantity
            event.changed_by = request.user
            event.save()
            if event.resource:
                if ct.consumes_resources():
                    resource = event.resource
                    resource.quantity += delta
                    resource.changed_by=request.user
                    resource.save()
    else:
        if ct.consumes_resources():    
            resource.quantity -= quantity
            resource.changed_by=request.user
            resource.save()
        event = EconomicEvent(
            resource = resource,
            commitment = ct,
            event_date = event_date,
            event_type = ct.event_type,
            to_agent = agent,
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

def citation_event_for_commitment(request):
    id = request.POST.get("id")
    resource_id = request.POST.get("resourceId")
    cited = int(request.POST.get("cited"))
    event_date = request.POST.get("eventDate")
    if event_date:
        event_date = datetime.datetime.strptime(event_date, '%Y-%m-%d').date()
    else:
        event_date = datetime.date.today()
    #import pdb; pdb.set_trace()
    ct = get_object_or_404(Commitment, pk=id)
    resource = get_object_or_404(EconomicResource, pk=resource_id)
    agent = get_agent(request)
    #import pdb; pdb.set_trace()
    quantity = Decimal("1")
    event = None
    events = ct.fulfillment_events.filter(resource=resource)
    if events:
        event = events[events.count() - 1]
    if event:
        if not cited:
            event.delete()
    else:
        event = EconomicEvent(
            resource = resource,
            commitment = ct,
            event_date = event_date,
            event_type = ct.event_type,
            from_agent = agent,
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

def time_use_event_for_commitment(request):
    id = request.POST.get("id")
    resource_id = request.POST.get("resourceId")
    quantity = request.POST.get("quantity")
    event_date = request.POST.get("eventDate")
    if event_date:
        event_date = datetime.datetime.strptime(event_date, '%Y-%m-%d').date()
    #import pdb; pdb.set_trace()
    ct = get_object_or_404(Commitment, pk=id)
    resource = get_object_or_404(EconomicResource, pk=resource_id)
    agent = get_agent(request)
    #import pdb; pdb.set_trace()
    quantity = Decimal(quantity)
    event = None
    events = ct.fulfillment_events.filter(resource=resource)
    if not event_date:
        event_date = datetime.date.today()
    if events:
        event = events[events.count() - 1]
    if event:
        if event.quantity != quantity:
            delta = event.quantity - quantity
            event.quantity = quantity
            event.changed_by = request.user
            event.save()
            if event.resource:
                if ct.consumes_resources():
                    resource = event.resource
                    resource.quantity += delta
                    resource.changed_by=request.user
                    resource.save()
    else:
        if ct.consumes_resources():    
            resource.quantity -= quantity
            resource.changed_by=request.user
            resource.save()
        event = EconomicEvent(
            resource = resource,
            commitment = ct,
            event_date = event_date,
            event_type = ct.event_type,
            to_agent = agent,
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
    event_date = request.POST.get("eventDate")
    if event_date:
        event_date = datetime.datetime.strptime(event_date, '%Y-%m-%d').date()
    else:
        event_date = datetime.date.today()
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        failure_form = FailedOutputForm(data=request.POST)
        if failure_form.is_valid():
            ct = get_object_or_404(Commitment, id=commitment_id)
            agent = get_agent(request)
            resource_type = ct.resource_type
            process = ct.process
            event = failure_form.save(commit=False)
            data = failure_form.cleaned_data
            quantity = data["quantity"]
            description = data["description"]
            unit_type = resource_type.unit.unit_type
            ets = EventType.objects.filter(
                resource_effect="<",
                unit_type=unit_type)
            if ets:
                event_type = ets[0]
            else:
                et_name = " ".join(["Failed", unit_type])
                event_type = EventType(
                    name=et_name,
                    resource_effect="<",
                    unit_type=unit_type)
                event_type.save()
            resource = EconomicResource(
                resource_type = ct.resource_type,
                created_date = event_date,
                quantity = quantity,
                quality = Decimal("-1"),
                unit_of_quantity = ct.unit_of_quantity,
                notes = description,
                created_by=request.user,
            )
            resource.save() 
            event.resource = resource              
            event.event_date = event_date
            event.event_type = event_type
            event.from_agent = agent
            event.resource_type = ct.resource_type
            event.process = process
            event.project = ct.project
            event.unit_of_quantity = ct.unit_of_quantity
            event.quality = Decimal("-1")
            event.created_by = request.user
            event.changed_by = request.user
            event.save()
            data = unicode(ct.failed_output_qty())
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
            if just_save:
                return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/process', process.id))
            elif keep_going:
                return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/change-process', process.id))
    return render_to_response("valueaccounting/create_process.html", {
        "demand_form": demand_form,
        "process_form": process_form,
        "output_formset": output_formset,
        "input_formset": input_formset,
    }, context_instance=RequestContext(request))

@login_required
def copy_process(request, process_id):
    process = get_object_or_404(Process, id=process_id)
    #import pdb; pdb.set_trace()
    #todo: is this correct? maybe not.
    demand = process.independent_demand()
    demand_form = DemandSelectionForm(data=request.POST or None)
    process_init = {
        "project": process.project,
        "url": process.url,
        "notes": process.notes,
    }      
    process_form = ProcessForm(initial=process_init, data=request.POST or None)
    output_init = []
    for op in process.outgoing_commitments():
        output_init.append({
            'resource_type': op.resource_type, 
            'quantity': op.quantity, 
            'description': op.description, 
            'unit_of_quantity': op.unit_of_quantity,
        })
    input_init = []
    for ip in process.incoming_commitments():
        input_init.append({
            'resource_type': ip.resource_type, 
            'quantity': ip.quantity, 
            'description': ip.description, 
            'unit_of_quantity': ip.unit_of_quantity,
        })
    OutputFormSet = modelformset_factory(
        Commitment,
        form=ProcessOutputForm,
        can_delete=True,
        extra=2,
        )
    output_formset = OutputFormSet(
        queryset=Commitment.objects.none(),
        initial=output_init,
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
        initial=input_init,
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
            if just_save:
                return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/process', process.id))
            elif keep_going:
                return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/change-process', process.id))
    return render_to_response("valueaccounting/create_process.html", {
        "demand": demand,
        "demand_form": demand_form,
        "process_form": process_form,
        "output_formset": output_formset,
        "input_formset": input_formset,
    }, context_instance=RequestContext(request))

@login_required
def change_work_event(request, event_id):
    event = get_object_or_404(EconomicEvent, id=event_id)
    commitment = event.commitment
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        form = WorkEventChangeForm(instance=event, data=request.POST)
        if form.is_valid():
            data = form.cleaned_data
            form.save()
    return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/labnote', commitment.id))
            

@login_required
def change_process(request, process_id):
    process = get_object_or_404(Process, id=process_id)
    demand = process.independent_demand()
    existing_demand = demand
    if demand:
        init = {}
        if not demand.receiver:
            init = {'create_order': True,}
        rand_form = RandOrderForm(
            instance=demand,
            data=request.POST or None,
            initial=init)
        demand_form = None
    else:
        demand_form = DemandSelectionForm(data=request.POST or None)    
        rand_form = RandOrderForm(data=request.POST or None)
    process_form = ProcessForm(instance=process, data=request.POST or None)
    OutputFormSet = modelformset_factory(
        Commitment,
        form=ProcessOutputForm,
        can_delete=True,
        extra=1,
        )
    output_formset = OutputFormSet(
        queryset=process.outgoing_commitments(),
        data=request.POST or None,
        prefix='output')
    CitationFormSet = modelformset_factory(
        Commitment,
        form=ProcessCitationCommitmentForm,
        can_delete=True,
        extra=2,
        )
    citation_formset = CitationFormSet(
        queryset=process.citation_requirements(),
        data=request.POST or None,
        prefix='citation')
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
            #import pdb; pdb.set_trace()
            #todo: always creates a rand. the form is always valid.
            if rand_form.is_valid():
                rand_data = rand_form.cleaned_data
                receiver = rand_data['receiver']
                provider = rand_data['provider']
                create_order = rand_data['create_order']
                if create_order or demand or receiver or provider:
                    demand = rand_form.save(commit=False)
                    if existing_demand:
                        if create_order:
                            demand.order_type = 'rand'
                        demand.changed_by = request.user
                    else:
                        demand.order_type = 'rand'
                        demand.created_by = request.user
                    demand.due_date = process.end_date
                    demand.save()
            if demand_form:
                if demand_form.is_valid():
                    selected_demand = demand_form.cleaned_data["demand"]
                    if selected_demand:
                        demand = selected_demand             
            for form in output_formset.forms:
                if form.is_valid():
                    output_data = form.cleaned_data
                    qty = output_data["quantity"]
                    ct_from_id = output_data["id"]
                    if qty:
                        ct = form.save(commit=False)
                        ct.order = demand
                        ct.independent_demand = demand
                        ct.project = process.project
                        ct.due_date = process.end_date
                        if ct_from_id:
                            ct.changed_by = request.user
                        else:
                            ct.process = process
                            ct.created_by = request.user
                            rt = output_data["resource_type"]
                            rel = ResourceRelationship.objects.get(
                                materiality=rt.materiality,
                                related_to="process",
                                direction="out")
                            ct.relationship = rel
                            ct.event_type = rel.event_type
                        ct.save()
                        if process.name == "Make something":
                            process.name = " ".join([
                                        "Make",
                                        rt.name,
                                    ])
                            process.save()
                    elif ct_from_id:
                        ct = form.save()
                        ct.delete()
            for form in citation_formset.forms:
                if form.is_valid():
                    citation_data = form.cleaned_data
                    if citation_data:
                        cited = citation_data["quantity"]
                        ct_from_id = citation_data["id"]
                        if cited:
                            rt = citation_data["resource_type"]
                            if rt:
                                ct = form.save(commit=False)
                                ct.independent_demand = demand
                                ct.project = process.project
                                ct.due_date = process.end_date
                                ct.quantity = Decimal("1")
                                if ct_from_id:
                                    old_ct = Commitment.objects.get(id=ct_from_id.id)
                                    old_rt = old_ct.resource_type
                                    if not old_rt == rt:
                                        rel = ResourceRelationship.objects.get(
                                            materiality=rt.materiality,
                                            direction="cite")
                                        ct.relationship = rel
                                        ct.event_type = rel.event_type
                                        unit = rel.unit or rt.unit
                                        ct.unit_of_quantity = unit
                                        ct.changed_by = request.user
                                else:
                                    ct.process = process
                                    ct.created_by = request.user
                                    rel = ResourceRelationship.objects.get(
                                        materiality=rt.materiality,
                                        direction="cite")
                                    ct.relationship = rel
                                    ct.event_type = rel.event_type
                                    unit = rel.unit or rt.unit
                                    ct.unit_of_quantity = unit
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
                    #import pdb; pdb.set_trace()
                    if not qty:
                        if ct_from_id:
                            ct = form.save()
                            trash = []
                            collect_lower_trash(ct, trash)
                            for proc in trash:
                                if proc.outgoing_commitments().count() <= 1:
                                    proc.delete()
                            ct.delete()
                    else:
                        ct = form.save(commit=False)
                        ct.independent_demand = demand
                        if ct_from_id:
                            producers = ct.resource_type.producing_commitments()
                            propagators = []
                            old_ct = Commitment.objects.get(id=ct_from_id.id)
                            old_rt = old_ct.resource_type
                            explode = True
                            for pc in producers:
                                if demand:
                                    if pc.independent_demand == demand:
                                        propagators.append(pc) 
                                        explode = False
                                    elif pc.independent_demand == existing_demand:
                                        propagators.append(pc) 
                                        explode = False
                                else:
                                    if pc.due_date == process.start_date:
                                        if pc.quantity == old_ct.quantity:
                                            propagators.append(pc)
                                            explode = False 
                            if ct.resource_type != old_rt:
                                old_ct.delete()
                                for ex_ct in old_rt.producing_commitments():
                                    if demand == ex_ct.independent_demand:
                                        trash = []
                                        collect_trash(ex_ct, trash)
                                        for proc in trash:
                                            #todo: feeder process with >1 outputs 
                                            # shd find the correct output to delete
                                            # and keep the others
                                            if proc.outgoing_commitments().count() <= 1:
                                                proc.delete()
                                explode = True                                 
                            elif qty != old_ct.quantity:
                                delta = qty - old_ct.quantity
                                for pc in propagators:
                                    if demand != existing_demand:
                                        propagate_changes(pc, delta, existing_demand, demand)
                                    else:
                                        propagate_qty_change(pc, delta) 
                            else:
                                if demand != existing_demand:
                                    delta = Decimal("0")
                                    for pc in propagators:
                                        propagate_changes(pc, delta, existing_demand, demand)                    
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
            if just_save:
                return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/process', process.id))
            elif keep_going:
                return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/change-process', process.id))
    return render_to_response("valueaccounting/change_process.html", {
        "process": process,
        "rand_form": rand_form,
        "demand_form": demand_form,
        "process_form": process_form,
        "output_formset": output_formset,
        "citation_formset": citation_formset,
        "input_formset": input_formset,
    }, context_instance=RequestContext(request))

def explode_dependent_demands(commitment, user):
    #import pdb; pdb.set_trace()
    rt = commitment.resource_type
    ptrt = rt.main_producing_process_type_relationship()
    demand = commitment.independent_demand
    if ptrt:
        pt = ptrt.process_type
        start_date = commitment.due_date - datetime.timedelta(minutes=pt.estimated_duration)
        feeder_process = Process(
            name=pt.name,
            process_type=pt,
            project=pt.project,
            url=pt.url,
            end_date=commitment.due_date,
            start_date=start_date,
            created_by=user,
        )
        feeder_process.save()
        output_commitment = Commitment(
            independent_demand=demand,
            event_type=ptrt.relationship.event_type,
            relationship=ptrt.relationship,
            due_date=commitment.due_date,
            resource_type=rt,
            process=feeder_process,
            project=pt.project,
            quantity=commitment.quantity,
            unit_of_quantity=rt.unit,
            created_by=user,
        )
        output_commitment.save()
        generate_schedule(feeder_process, demand, user)

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

def propagate_changes(commitment, delta, old_demand, new_demand):
    #import pdb; pdb.set_trace()
    process = commitment.process
    for ic in process.incoming_commitments():
        ratio = ic.quantity / commitment.quantity 
        new_delta = (delta * ratio).quantize(Decimal('.01'), rounding=ROUND_UP)
        ic.quantity += new_delta
        ic.independent_demand = new_demand
        ic.save()
        rt = ic.resource_type
        demand = ic.independent_demand
        for pc in rt.producing_commitments():
            if pc.independent_demand == old_demand:
                propagate_changes(pc, new_delta, old_demand, new_demand)
    commitment.quantity += delta
    commitment.independent_demand = new_demand
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
                if just_save:
                    return HttpResponseRedirect('/%s/%s/'
                        % ('accounting/order-schedule', rand.id))
                elif keep_going:
                    return HttpResponseRedirect('/%s/%s/'
                        % ('accounting/change-rand', rand.id))
    return render_to_response("valueaccounting/create_rand.html", {
        "rand_form": rand_form,
        "process_form": process_form,
        "output_formset": output_formset,
        "input_formset": input_formset,
    }, context_instance=RequestContext(request))

@login_required
def copy_rand(request, rand_id):
    rand = get_object_or_404(Order, id=rand_id)
    #import pdb; pdb.set_trace()
    rand_init = {
        'receiver': rand.receiver, 
        'provider': rand.provider,
    }
    rand_form = RandOrderForm(initial=rand_init, data=request.POST or None)
    process = None
    for item in rand.producing_commitments():
        if item.process:
            process = item.process
            break
    process_init = {}
    output_init = []
    input_init = []
    if process:
        process_init = {
            "project": process.project,
            "url": process.url,
            "notes": process.notes,
        }      
        for op in process.outgoing_commitments():
            output_init.append({
                'resource_type': op.resource_type, 
                'quantity': op.quantity, 
                'description': op.description, 
                'unit_of_quantity': op.unit_of_quantity,
            })

        for ip in process.incoming_commitments():
            input_init.append({
                'resource_type': ip.resource_type, 
                'quantity': ip.quantity, 
                'description': ip.description, 
                'unit_of_quantity': ip.unit_of_quantity,
            })
    process_form = ProcessForm(initial=process_init, data=request.POST or None)
    OutputFormSet = modelformset_factory(
        Commitment,
        form=ProcessOutputForm,
        can_delete=True,
        extra=2,
        )
    output_formset = OutputFormSet(
        queryset=Commitment.objects.none(),
        initial=output_init,
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
        initial=input_init,
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
                if just_save:
                    return HttpResponseRedirect('/%s/%s/'
                        % ('accounting/order-schedule', rand.id))
                elif keep_going:
                    return HttpResponseRedirect('/%s/%s/'
                        % ('accounting/change-rand', rand.id))
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
        output_formset = OutputFormSet(
            queryset=Commitment.objects.none(),
            data=request.POST or None,
            prefix='output')
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
                                for proc in trash:
                                    if proc.outgoing_commitments().count() <= 1:
                                        proc.delete()
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
                                            for proc in trash:
                                                #todo: feeder process with >1 outputs 
                                                # shd find the correct output to delete
                                                # and keep the others
                                                if proc.outgoing_commitments().count() <= 1:
                                                    proc.delete()
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
                if just_save:
                    return HttpResponseRedirect('/%s/%s/'
                        % ('accounting/order-schedule', rand.id))
                elif keep_going:
                    return HttpResponseRedirect('/%s/%s/'
                        % ('accounting/change-rand', rand.id))
    return render_to_response("valueaccounting/change_rand.html", {
        "rand": rand,
        "rand_form": rand_form,
        "process_form": process_form,
        "output_formset": output_formset,
        "input_formset": input_formset,
    }, context_instance=RequestContext(request))

@login_required
def process_selections(request, rand=0):
    #import pdb; pdb.set_trace()
    resource_names = [res.name for res in EconomicResourceType.objects.process_outputs()]
    related_outputs = []
    related_citables = []
    related_inputs = []
    related_recipes = []
    resource_types = []
    selected_name = ""
    selected_name2 = ""
    #import pdb; pdb.set_trace()
    use_radio = True
    work_form = None
    project_form = None
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        input_resource_types = []
        input_process_types = []
        edit_process = request.POST.get("edit-process")
        labnotes = request.POST.get("labnotes")
        past = request.POST.get("past")
        get_related = request.POST.get("get-related")
        if get_related:
            selected_name = request.POST.get("resourceName")
            if selected_name:
                related_outputs = list(EconomicResourceType.objects.process_outputs().filter(name__icontains=selected_name))
                #related_outputs.extend(list(EconomicResourceType.objects.process_outputs().filter(category__name__icontains=selected_name)))
                related_citables = []
                citables = EconomicResourceType.objects.process_citables_with_resources()
                for c in citables:
                    name = c.name.lower()
                    sname = selected_name.lower()
                    if name.find(sname) >= 0:
                        related_citables.append(c)
                related_inputs = list(EconomicResourceType.objects.process_inputs().filter(name__icontains=selected_name))
                related_recipes = []
                for output in related_outputs:
                    ppt = output.main_producing_process_type()
                    if ppt:
                        if ppt not in related_recipes:
                            related_recipes.append(ppt)

            selected_name2 = request.POST.get("resourceName2")
            if selected_name2:
                #import pdb; pdb.set_trace()
                new_outputs = list(EconomicResourceType.objects.process_outputs().filter(name__icontains=selected_name2))
                related_outputs.extend(new_outputs)
                related_inputs.extend(list(EconomicResourceType.objects.process_inputs().filter(name__icontains=selected_name2)))
                for output in new_outputs:
                    ppt = output.main_producing_process_type()
                    if ppt:
                        if ppt not in related_recipes:
                            related_recipes.append(ppt)
            if len(related_recipes) == 1:
                use_radio = False
            work_form = WorkSelectionForm()
            project_form = ProjectSelectionForm()
        else:
            rp = request.POST
            work_form = WorkSelectionForm(data=rp)
            project = None
            project_form = ProjectSelectionForm(data=rp)
            if project_form.is_valid():
                project = project_form.cleaned_data["project"]
            #import pdb; pdb.set_trace()
            today = datetime.date.today()
            demand = None
            if rand:
                demand = Order(
                    order_type="rand",
                    due_date=today,
                    created_by=request.user)
                demand.save()
            else:
                demand = Order(
                    order_type="holder",
                    due_date=today,
                    created_by=request.user)
                demand.save()
            output_rts = []
            citable_rts = []
            input_rts = []
            pts = []
            for key, value in dict(rp).iteritems():
                if "input" in key:
                    input_id = int(value[0])
                    input_rt = EconomicResourceType.objects.get(id=input_id)
                    input_rts.append(input_rt)
                if "citable" in key:
                    citable_id = int(value[0])
                    citable_rt = EconomicResourceType.objects.get(id=citable_id)
                    citable_rts.append(citable_rt)
                if "output" in key:
                    output_id = int(value[0])
                    output_rt = EconomicResourceType.objects.get(id=output_id)
                    output_rts.append(output_rt)
                if "recipe" in key:
                    recipe_id = int(value[0])
                    pt = ProcessType.objects.get(id=recipe_id)
                    pts.append(pt)
            pt = None
            name = "Make something"
            if output_rts:
                name = " ".join([
                    "Make",
                    output_rts[0].name,
                ])
            if len(pts) == 1:
                pt = pts[0]
                process = Process(
                    name=name,
                    process_type=pt,
                    project=pt.project,
                    url=pt.url,
                    end_date=today,
                    start_date=today,
                    created_by=request.user,
                )
                process.save()
            else:
                for ptx in pts:
                    for rt in ptx.produced_resource_types():
                        if rt in output_rts:
                            pt = ptx
                if pt:
                    process = Process(
                        name=name,
                        process_type=pt,
                        project=pt.project,
                        url=pt.url,
                        end_date=today,
                        start_date=today,
                        created_by=request.user,
                    )
                    process.save()
                else:
                    process = Process(
                        name=name,
                        end_date=today,
                        start_date=today,
                        created_by=request.user,
                        project=project,
                    )
                    process.save()
            if pt:
                resource_types.extend(pt.produced_resource_types())
                for ptrt in pt.consumed_resource_type_relationships():
                    rel = ptrt.relationship
                    rtype = ptrt.resource_type
                    commitment = Commitment(
                        process=process,
                        independent_demand=demand,
                        project=process.project,
                        event_type=rel.event_type,
                        relationship=rel,
                        due_date=today,
                        resource_type=rtype,
                        quantity=ptrt.quantity,
                        unit_of_quantity=ptrt.unit_of_quantity,
                        created_by=request.user,
                    )
                    commitment.save()
                    explode_dependent_demands(commitment, request.user)         
            for rt in output_rts:
                rel = ResourceRelationship.objects.get(
                    materiality=rt.materiality,
                    related_to="process",
                    direction="out")
                if rel:
                    commitment = Commitment(
                        process=process,
                        order=demand,
                        independent_demand=demand,
                        project=process.project,
                        event_type=rel.event_type,
                        relationship=rel,
                        due_date=today,
                        resource_type=rt,
                        quantity=Decimal("1"),
                        unit_of_quantity=rt.unit,
                        created_by=request.user,
                    )
                    commitment.save()
            for rt in citable_rts:
                rel = ResourceRelationship.objects.get(
                    materiality=rt.materiality,
                    direction="cite")
                if rel:
                    commitment = Commitment(
                        process=process,
                        independent_demand=demand,
                        project=process.project,
                        event_type=rel.event_type,
                        relationship=rel,
                        due_date=today,
                        resource_type=rt,
                        quantity=Decimal("1"),
                        unit_of_quantity=rt.unit,
                        created_by=request.user,
                    )
                    commitment.save()
            resource_types.extend([ic.resource_type for ic in process.incoming_commitments()])
            for rt in input_rts:
                #import pdb; pdb.set_trace()
                if rt not in resource_types:
                    rel = ResourceRelationship.objects.get(
                        materiality=rt.materiality,
                        related_to="process",
                        direction="in")
                    if rel:
                        commitment = Commitment(
                            process=process,
                            independent_demand=demand,
                            project=process.project,
                            event_type=rel.event_type,
                            relationship=rel,
                            due_date=today,
                            resource_type=rt,
                            quantity=Decimal("1"),
                            unit_of_quantity=rt.unit,
                            created_by=request.user,
                        )
                        commitment.save()
                        explode_dependent_demands(commitment, request.user)
            if work_form.is_valid():
                #import pdb; pdb.set_trace()
                agent = get_agent(request)
                if agent:
                    rt_id = work_form.cleaned_data["type_of_work"]
                    rt = EconomicResourceType.objects.get(id=rt_id)
                    rel = ResourceRelationship.objects.get(
                        materiality=rt.materiality,
                        related_to="process",
                        direction="in")
                    if rel:
                        work_commitment = Commitment(
                            process=process,
                            independent_demand=demand,
                            project=process.project,
                            event_type=rel.event_type,
                            from_agent=agent,
                            relationship=rel,
                            due_date=today,
                            resource_type=rt,
                            quantity=Decimal("1"),
                            unit_of_quantity=rt.unit,
                            created_by=request.user,
                        )
                        work_commitment.save()
            if edit_process:
                return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/change-process', process.id))  
            if labnotes:
                return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/work-commitment', work_commitment.id)) 
            if past:
                return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/past-work', work_commitment.id))            
                            
    return render_to_response("valueaccounting/process_selections.html", {
        "resource_names": resource_names,
        "related_outputs": related_outputs,
        "related_citables": related_citables,
        "related_inputs": related_inputs,
        "related_recipes": related_recipes,
        "selected_name": selected_name,
        "selected_name2": selected_name2,
        "use_radio": use_radio,
        "work_form": work_form,
        "project_form": project_form,
    }, context_instance=RequestContext(request))

