import datetime
import time
import csv
from operator import attrgetter

from django.db.models import Q
from django.http import Http404
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
from django.forms.models import formset_factory, modelformset_factory, BaseModelFormSet
from django.forms import ValidationError
from django.utils import simplejson
from django.utils.datastructures import SortedDict
from django.contrib.auth.forms import UserCreationForm

from valuenetwork.valueaccounting.models import *
#from valuenetwork.valueaccounting.views import *
from valuenetwork.valueaccounting.forms import *
from valuenetwork.valueaccounting.utils import *

def get_agent(request):
    agent = None
    try:
        au = request.user.agent
        agent = au.agent
    except:
        pass
    return agent

def get_help(page_name):
    try:
        return Help.objects.get(page=page_name)
    except Help.DoesNotExist:
        return None

def home(request):
    work_to_do = Commitment.objects.unfinished().filter(
            from_agent=None, 
            event_type__relationship="work")
    #todo: reqs needs a lot of work
    reqs = Commitment.objects.unfinished().filter(
        event_type__relationship="in").order_by("resource_type__name")
    stuff = SortedDict()
    for req in reqs:
        if req.quantity_to_buy():
            if req.resource_type not in stuff:
                stuff[req.resource_type] = Decimal("0")
            stuff[req.resource_type] += req.quantity_to_buy()
    #treqs = Commitment.objects.unfinished().filter(
    #    event_type__relationship="in").order_by("resource_type__name")
    #for req in treqs:
    #    if req.quantity_to_buy():
    #        if req.resource_type not in stuff:
    #            stuff[req.resource_type] = req.quantity_to_buy()
    vcs = Commitment.objects.filter(event_type__relationship="out")
    value_creations = []
    rts = []
    for vc in vcs:
        if vc.fulfilling_events():
            if vc.resource_type not in rts:
                rts.append(vc.resource_type)
                value_creations.append(vc)
    return render_to_response("homepage.html", {
        "work_to_do": work_to_do,
        "stuff_to_buy": stuff,
        "value_creations": value_creations,
        "photo_size": (128, 128),
        "help": get_help("home"),
    }, context_instance=RequestContext(request))

@login_required
def create_user_and_agent(request):
    if not request.user.is_superuser:
        return render_to_response('valueaccounting/no_permission.html')
    user_form = UserCreationForm(data=request.POST or None)
    agent_form = AgentForm(data=request.POST or None)
    agent_selection_form = AgentSelectionForm()
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        sa_id = request.POST.get("selected_agent")
        agent = None
        if sa_id:
            agent = EconomicAgent.objects.get(id=sa_id)
        if user_form.is_valid():
            user = user_form.save(commit=False)
            user.first_name = request.POST.get("first_name")
            user.last_name = request.POST.get("last_name")
            user.email = request.POST.get("email")
            nick = request.POST.get("nick")
            description = request.POST.get("description")
            url = request.POST.get("url")
            address = request.POST.get("address")
            email = request.POST.get("email")
            agent_type_id = request.POST.get("agent_type")
            errors = False
            if agent:
                agent.description = description
                agent.url = url
                agent.address = address
                if agent_type_id:
                    if agent.agent_type.id != agent_type_id:
                        agent_type = AgentType.objects.get(id=agent_type_id)
                        agent.agent_type = agent_type
                if not agent.email:
                    agent.email = email
            else:
                if nick and user.first_name:
                    try:
                        agent = EconomicAgent.objects.get(nick=nick)
                        errors = True
                    except EconomicAgent.DoesNotExist:
                        pass
                else:
                    errors = True
                if not errors:
                    name = " ".join([user.first_name, user.last_name])
                    agent_type = AgentType.objects.get(id=agent_type_id)
                    agent = EconomicAgent(
                        nick = nick,
                        name = name,
                        description = description,
                        url = url,
                        address = address,
                        agent_type = agent_type,
                    )  
            if errors:
                agent_form.is_valid()
            else:
                user.save()           
                agent.save()
                au = AgentUser(
                    agent = agent,
                    user = user)
                au.save()
                return HttpResponseRedirect("/admin/valueaccounting/economicagent/")
    
    return render_to_response("valueaccounting/create_user_and_agent.html", {
        "user_form": user_form,
        "agent_form": agent_form,
        "agent_selection_form": agent_selection_form,
    }, context_instance=RequestContext(request))

def projects(request):
    roots = Project.objects.filter(parent=None)
    agent = get_agent(request)
    project_create_form = ProjectForm()
    
    return render_to_response("valueaccounting/projects.html", {
        "roots": roots,
        "agent": agent,
        "help": get_help("projects"),
        "project_create_form": project_create_form,
    }, context_instance=RequestContext(request))

def create_project(request):
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            form.save()
    return HttpResponseRedirect("/accounting/projects/")

@login_required
def test_patterns(request):
    pattern_form = PatternSelectionForm(data=request.POST or None)
    pattern = None
    slots = []
    if request.method == "POST":
        if pattern_form.is_valid():
            pattern = pattern_form.cleaned_data["pattern"]
            slots = pattern.event_types()
            #import pdb; pdb.set_trace()
            for slot in slots:
                slot.resource_types = pattern.get_resource_types(slot)
                slot.facets = pattern.facets_for_event_type(slot)
    
    return render_to_response("valueaccounting/test_patterns.html", {
        "pattern_form": pattern_form,
        "pattern": pattern,
        "slots": slots,
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

def select_resource_types(facet_values):
    """ Logic:
        Facet values in different Facets are ANDed.
        Ie, a resource type must have all of those facet values.
        Facet values in the same Facet are ORed.
        Ie, a resource type must have at least one of those facet values.
    """
    #import pdb; pdb.set_trace()
    fv_ids = [fv.id for fv in facet_values]
    rt_facet_values = ResourceTypeFacetValue.objects.filter(facet_value__id__in=fv_ids)
    rts = [rtfv.resource_type for rtfv in rt_facet_values]
    answer = []
    singles = [] #Facets with only one facet_value in the Pattern
    multis = []  #Facets with more than one facet_value in the Pattern
    aspects = {}
    for fv in facet_values:
        if fv.facet not in aspects:
            aspects[fv.facet] = []
        aspects[fv.facet].append(fv)
    for facet, facet_values in aspects.items():
        if len(facet_values) > 1:
            for fv in facet_values:
                multis.append(fv)
        else:
            singles.append(facet_values[0])
    single_ids = [s.id for s in singles]
    #import pdb; pdb.set_trace()
    for rt in rts:
        rt_singles = [rtfv.facet_value for rtfv in rt.facets.filter(facet_value_id__in=single_ids)]
        rt_multis = [rtfv.facet_value for rtfv in rt.facets.exclude(facet_value_id__in=single_ids)]
        if set(rt_singles) == set(singles):
            if not rt in answer:
                if multis:
                    # if multis intersect
                    if set(rt_multis) & set(multis):
                        answer.append(rt)
                else:
                    answer.append(rt)
    answer_ids = [a.id for a in answer]
    return list(EconomicResourceType.objects.filter(id__in=answer_ids))

def resource_types(request):
    roots = EconomicResourceType.objects.all()
    resource_names = '~'.join([
        res.name for res in roots])
    create_form = EconomicResourceTypeForm()
    create_formset = create_facet_formset()
    facets = Facet.objects.all()
    select_all = True
    selected_values = "all"
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        selected_values = request.POST["categories"]
        if selected_values:
            vals = selected_values.split(",")
            if vals[0] == "all":
                select_all = True
                roots = EconomicResourceType.objects.all()
            else:
                select_all = False
                fvs = []
                for val in vals:
                    val_split = val.split(":")
                    fname = val_split[0]
                    fvalue = val_split[1].strip()
                    fvs.append(FacetValue.objects.get(facet__name=fname,value=fvalue))
                roots = select_resource_types(fvs)
                roots.sort(key=lambda rt: rt.label())
    return render_to_response("valueaccounting/resource_types.html", {
        "roots": roots,
        "facets": facets,
        "select_all": select_all,
        "selected_values": selected_values,
        "create_form": create_form,
        "create_formset": create_formset,
        "photo_size": (128, 128),
        "help": get_help("resource_types"),
        "resource_names": resource_names,
    }, context_instance=RequestContext(request))

def resource_type(request, resource_type_id):
    resource_type = get_object_or_404(EconomicResourceType, id=resource_type_id)
    names = EconomicResourceType.objects.values_list('name', flat=True)
    resource_names = '~'.join(names)
    init = {"unit_of_quantity": resource_type.unit,}
    create_form = CreateEconomicResourceForm(
        data=request.POST or None, 
        files=request.FILES or None,
        initial=init)
    if request.method == "POST":
        if create_form.is_valid():
            resource = create_form.save(commit=False)
            resource.resource_type = resource_type
            resource.save()
            return HttpResponseRedirect('/%s/%s/'
                % ('accounting/resource', resource.id))
                       
    return render_to_response("valueaccounting/resource_type.html", {
        "resource_type": resource_type,
        "photo_size": (128, 128),
        "resource_names": resource_names,
        "create_form": create_form,
    }, context_instance=RequestContext(request))

def inventory(request):
    #import pdb; pdb.set_trace()
    #resources = EconomicResource.objects.select_related().filter(quantity__gt=0).order_by('resource_type')
    rts = EconomicResourceType.objects.all()
    resource_types = []
    facets = Facet.objects.all()
    select_all = True
    selected_values = "all"
    if request.method == "POST":
        selected_values = request.POST["categories"]
        vals = selected_values.split(",")
        if vals[0] == "all":
            select_all = True
            #resources = EconomicResource.objects.select_related().filter(quantity__gt=0).order_by('resource_type')
            for rt in rts:
                if rt.onhand_qty()>0:
                    resource_types.append(rt)
        else:
            select_all = False
            #resources = EconomicResource.objects.select_related().filter(quantity__gt=0, resource_type__category__name__in=vals).order_by('resource_type')
            fvs = []
            for val in vals:
                val_split = val.split(":")
                fname = val_split[0]
                fvalue = val_split[1].strip()
                fvs.append(FacetValue.objects.get(facet__name=fname,value=fvalue))
            rts = select_resource_types(fvs)
            for rt in rts:
                if rt.onhand_qty()>0:
                    resource_types.append(rt)
            resource_types.sort(key=lambda rt: rt.label())
    else:
        for rt in rts:
            if rt.onhand_qty()>0:
                resource_types.append(rt)
    return render_to_response("valueaccounting/inventory.html", {
        #"resources": resources,
        "resource_types": resource_types,
        "facets": facets,
        "select_all": select_all,
        "selected_values": selected_values,
        "photo_size": (128, 128),
        "help": get_help("inventory"),
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
    #todo: this whole thing is obsolete
    resource_types = EconomicResourceType.objects.all()
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
            pattern = None
            try:
                pattern = PatternUseCase.objects.get(use_case='non_prod').pattern
            except PatternUseCase.DoesNotExist:
                raise ValidationError("no non-production ProcessPattern")
            if pattern:
                unit = Unit.objects.filter(
                    unit_type="time",
                    name__icontains="Hours")[0]
                for event in events:
                    if event.event_date and event.quantity:
                        event.from_agent=member
                        event.is_contribution=True
                        rt = event.resource_type
                        event_type = pattern.event_type_for_resource_type("work", rt)
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


@login_required
def log_simple(request):
    member = get_agent(request)
    if not member:
        return HttpResponseRedirect('/%s/'
            % ('accounting/start')) 
    pattern = PatternUseCase.objects.get(use_case='design').pattern  #assumes only one pattern is assigned to design
    output_form = SimpleOutputForm(data=request.POST or None)
    resource_form = SimpleOutputResourceForm(data=request.POST or None, prefix='resource', pattern=pattern)
    work_form = SimpleWorkForm(data=request.POST or None, prefix='work', pattern=pattern)
    citations_select_form = SelectCitationResourceForm(data=request.POST or None, prefix='cite', pattern=pattern)
    rt_create_form = EconomicResourceTypeAjaxForm()
    rtf_create_formset = create_patterned_facet_formset(pattern=pattern, slot="out")
    facets = pattern.output_facets()
    names = EconomicResourceType.objects.values_list('name', flat=True)
    resource_names = '~'.join(names)

    if request.method == "POST":
        #import pdb; pdb.set_trace()
        if output_form.is_valid():
            output_event = output_form.save(commit=False)
            if work_form.is_valid():
                work_event = work_form.save(commit=False)
                if resource_form.is_valid():
                    output_resource = resource_form.save(commit=False)
                    
                    process = Process()
                    process.name = 'Create ' + output_resource.identifier
                    process.project = output_event.project
                    process.start_date = output_event.event_date
                    process.end_date = output_event.event_date
                    process.started = output_event.event_date
                    process.finished = True
                    process.created_by = request.user
                    process.save()                    
                    
                    output_resource.quantity = 1
                    output_resource.unit_of_quantity = output_resource.resource_type.directional_unit("out") 
                    #output_resource.author = member
                    output_resource.created_by = request.user
                    output_resource.save()

                    output_event.event_type = pattern.event_type_for_resource_type("out", output_resource.resource_type)
                    output_event.process = process
                    output_event.resource_type = output_resource.resource_type 
                    output_event.quantity = output_resource.quantity 
                    output_event.unit_of_quantity = output_resource.unit_of_quantity 
                    output_event.resource = output_resource
                    output_event.from_agent = member
                    output_event.created_by = request.user
                    output_event.save()

                    work_event.event_type = pattern.event_type_for_resource_type("work", work_event.resource_type)
                    work_event.event_date = output_event.event_date
                    work_event.process = process
                    work_event.project = output_event.project
                    work_event.is_contribution = True
                    work_event.unit_of_quantity = work_event.resource_type.directional_unit("use")  
                    work_event.from_agent = member
                    work_event.created_by = request.user
                    work_event.save()

                    #import pdb; pdb.set_trace()
                    citation_resources = request.POST.getlist("citation")
                    if citation_resources:
                        for cr_id in citation_resources:
                            cr = EconomicResource.objects.get(id=int(cr_id))
                            citation_event = EconomicEvent()
                            citation_event.event_type = pattern.event_type_for_resource_type("cite", cr.resource_type)
                            citation_event.event_date = output_event.event_date
                            citation_event.process = process
                            citation_event.project = output_event.project
                            citation_event.resource = cr
                            citation_event.resource_type = cr.resource_type
                            citation_event.quantity = 1
                            citation_event.unit_of_quantity = citation_event.resource_type.directional_unit("cite")  
                            citation_event.from_agent = member
                            citation_event.created_by = request.user
                            citation_event.save()

                    return HttpResponseRedirect('/%s/%s/'
                        % ('accounting/resource', output_resource.id ))

                else:
                    raise ValidationError(resource_form.errors)
            else:
                raise ValidationError(work_form.errors)
        else:
            raise ValidationError(output_form.errors)

    return render_to_response("valueaccounting/log_simple.html", {
        "member": member,
        "output_form": output_form,
        "work_form": work_form,
        "resource_form":resource_form,
        "citations_select_form": citations_select_form,
        "rt_create_form": rt_create_form,
        "rtf_create_formset": rtf_create_formset,
        "facets": facets,
        "pattern": pattern,
        "resource_names": resource_names,
    }, context_instance=RequestContext(request))

def json_resource_type_resources(request, resource_type_id):
    #import pdb; pdb.set_trace()
    json = serializers.serialize("json", EconomicResource.objects.filter(resource_type=resource_type_id), fields=('identifier'))
    return HttpResponse(json, mimetype='application/json')


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
    facets = Facet.objects.all()
    if request.method == "POST":
        nodes = generate_xbill(rt)
        depth = 1
        for node in nodes:
            depth = max(depth, node.depth)
        selected_vals = request.POST["categories"]
        vals = selected_vals.split(",")
        selected_depth = int(request.POST['depth'])
        #import pdb; pdb.set_trace()
        if vals[0]:
            if vals[0] == "all":
                select_all = True
            else:
                select_all = False
                fvs = []
                for val in vals:
                    val_split = val.split(":")
                    fname = val_split[0]
                    fvalue = val_split[1].strip()
                    fvs.append(FacetValue.objects.get(facet__name=fname,value=fvalue))
        for node in nodes:
            node.show = False
            if node.depth <= selected_depth:
                if select_all:
                    node.show = True
                else:
                    #import pdb; pdb.set_trace()
                    if node.xbill_class == "economic-resource-type":
                        if node.xbill_object().matches_filter(fvs):
                            node.show = True
                    else:
                        node.show = True
    else:
        nodes = generate_xbill(rt)
        depth = 1
        for node in nodes:
            depth = max(depth, node.depth)
            node.show = True
        selected_depth = depth
        select_all = True
        selected_vals = "all"
    return render_to_response("valueaccounting/extended_bill.html", {
        "resource_type": rt,
        "nodes": nodes,
        "depth": depth,
        "selected_depth": selected_depth,
        "facets": facets,
        "select_all": select_all,
        "selected_vals": selected_vals,
        "photo_size": (128, 128),
        "big_photo_size": (200, 200),
        "help": get_help("recipes"),
    }, context_instance=RequestContext(request))

@login_required
def edit_extended_bill(request, resource_type_id):
    #import time
    #start_time = time.time()
    rt = get_object_or_404(EconomicResourceType, pk=resource_type_id)
    #import pdb; pdb.set_trace()
    nodes = generate_xbill(rt)
    resource_type_form = EconomicResourceTypeChangeForm(instance=rt)
    feature_form = FeatureForm()
    names = EconomicResourceType.objects.values_list('name', flat=True)
    resource_names = '~'.join(names)
    #end_time = time.time()
    #print("edit_extended_bill view elapsed time was %g seconds" % (end_time - start_time))
    return render_to_response("valueaccounting/edit_xbill.html", {
        "resource_type": rt,
        "nodes": nodes,
        "photo_size": (128, 128),
        "big_photo_size": (200, 200),
        "resource_type_form": resource_type_form,
        "feature_form": feature_form,
        "resource_names": resource_names,
        "help": get_help("edit_recipes"),
    }, context_instance=RequestContext(request))

@login_required
def change_resource_type(request, resource_type_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        rt = get_object_or_404(EconomicResourceType, pk=resource_type_id)
        form = EconomicResourceTypeChangeForm(request.POST, request.FILES, instance=rt)
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
            #visited_resources.add(ct.resource_type)
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
                #visited_resources.add(ct.resource_type)
                collect_trash(ct, trash, visited_resources)
                #import pdb; pdb.set_trace()
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
                        if ct.process not in processes:
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
    #import pdb; pdb.set_trace()
    order = commitment.independent_demand
    process = commitment.process
    if process:
        if process in trash:
            return trash
        trash.append(process)
        for inp in process.incoming_commitments():
            resource_type = inp.resource_type
            if resource_type not in visited_resources:
                #visited_resources.add(resource_type)
                pcs = resource_type.producing_commitments()
                if pcs:
                    for pc in pcs:
                        if pc.independent_demand == order:
                            collect_trash(pc, trash, visited_resources)
    return trash

def collect_lower_trash(commitment, trash, visited_resources):
    order = commitment.independent_demand
    resource_type = commitment.resource_type
    pcs = resource_type.producing_commitments()
    #visited_resources.add(resource_type)
    if pcs:
        for pc in pcs:
            if pc.independent_demand == order:
                collect_trash(pc, trash, visited_resources)
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
            formset = create_facet_formset(data=request.POST)
            for form_rtfv in formset.forms:
                if form_rtfv.is_valid():
                    data_rtfv = form_rtfv.cleaned_data
                    fv = FacetValue.objects.get(id=data_rtfv["value"])
                    if fv:
                        rtfv = ResourceTypeFacetValue()
                        rtfv.resource_type = rt
                        rtfv.facet_value = fv
                        rtfv.save()

            next = request.POST.get("next")
            if next:
                return HttpResponseRedirect(next)
            else:
                return HttpResponseRedirect('/%s/'
                    % ('accounting/resources'))
        else:
            raise ValidationError(form.errors)

@login_required
def create_resource_type_ajax(request):
    #import pdb; pdb.set_trace()
    slot = request.POST.get("slot")
    pt_id = int(request.POST.get("pt-id").replace("ProcessType-",""))
    process_type = ProcessType.objects.get(id=pt_id) 
    if slot == "cite":
        rt_prefix = process_type.xbill_citable_rt_prefix()
        rtf_prefix = process_type.xbill_citable_rt_facet_prefix()
    else: 
        rt_prefix = process_type.xbill_input_rt_prefix()  
        rtf_prefix = process_type.xbill_input_rt_facet_prefix()
    form = EconomicResourceTypeAjaxForm(request.POST, request.FILES, prefix=rt_prefix)
    if form.is_valid():
        data = form.cleaned_data
        rt = form.save(commit=False)                    
        rt.created_by=request.user
        rt.save()
        formset = process_type.create_facet_formset_filtered(data=request.POST, pre=rtf_prefix, slot=slot)
        for form_rtfv in formset.forms:
            if form_rtfv.is_valid():
                data_rtfv = form_rtfv.cleaned_data
                fv = FacetValue.objects.get(id=data_rtfv["value"])
                if fv:
                    rtfv = ResourceTypeFacetValue()
                    rtfv.resource_type = rt
                    rtfv.facet_value = fv
                    rtfv.save()
        return_data = serializers.serialize("json", EconomicResourceType.objects.filter(id=rt.id), fields=('id','name',)) 
        return HttpResponse(return_data, mimetype="text/json-comment-filtered")
    else:
        return HttpResponse(form.errors, mimetype="text/json-comment-filtered")

@login_required
def create_resource_type_simple_patterned_ajax(request):
    #import pdb; pdb.set_trace()
    form = EconomicResourceTypeAjaxForm(request.POST, request.FILES)
    if form.is_valid():
        data = form.cleaned_data
        rt = form.save(commit=False)                    
        rt.created_by=request.user
        rt.save()
        slot = request.POST["slot"]
        pattern_id = request.POST["pattern"]
        pattern = ProcessPattern.objects.get(id=pattern_id)
        formset = create_patterned_facet_formset(pattern, slot, data=request.POST)
        for form_rtfv in formset.forms:
            if form_rtfv.is_valid():
                data_rtfv = form_rtfv.cleaned_data
                fv = FacetValue.objects.get(id=data_rtfv["value"])
                if fv:
                    rtfv = ResourceTypeFacetValue()
                    rtfv.resource_type = rt
                    rtfv.facet_value = fv
                    rtfv.save()
        return_data = serializers.serialize("json", EconomicResourceType.objects.filter(id=rt.id), fields=('id','name',)) 
        return HttpResponse(return_data, mimetype="text/json-comment-filtered")
    else:
        return HttpResponse(form.errors, mimetype="text/json-comment-filtered")

@login_required
def create_process_type_input(request, process_type_id, slot):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        pt = get_object_or_404(ProcessType, pk=process_type_id)
        if slot == "c":
            prefix = pt.xbill_consumable_prefix()
            form = ProcessTypeConsumableForm(data=request.POST, process_type=pt, prefix=prefix)
        elif slot == "u":
            prefix = pt.xbill_usable_prefix()
            form = ProcessTypeUsableForm(data=request.POST, process_type=pt, prefix=prefix)
        if form.is_valid():
            ptrt = form.save(commit=False)
            rt = form.cleaned_data["resource_type"]
            ptrt.process_type=pt
            pattern = pt.process_pattern
            event_type = pattern.event_type_for_resource_type("in", rt)
            ptrt.event_type = event_type
            ptrt.created_by=request.user
            ptrt.save()
            next = request.POST.get("next")
            return HttpResponseRedirect(next)
        else:
            raise ValidationError(form.errors)

@login_required
def create_process_type_citable(request, process_type_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        pt = get_object_or_404(ProcessType, pk=process_type_id)
        prefix = pt.xbill_citable_prefix()
        form = ProcessTypeCitableForm(data=request.POST, process_type=pt, prefix=prefix)
        if form.is_valid():
            ptrt = form.save(commit=False)
            ptrt.quantity = Decimal("1.0")
            rt = form.cleaned_data["resource_type"]
            ptrt.unit_of_quantity = rt.unit
            ptrt.process_type=pt
            pattern = pt.process_pattern
            event_type = pattern.event_type_for_resource_type("cite", rt)
            ptrt.event_type = event_type
            ptrt.created_by=request.user
            ptrt.save()
            next = request.POST.get("next")
            return HttpResponseRedirect(next)
        else:
            raise ValidationError(form.errors)

@login_required
def create_process_type_work(request, process_type_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        pt = get_object_or_404(ProcessType, pk=process_type_id)
        prefix = pt.xbill_work_prefix()
        form = ProcessTypeWorkForm(data=request.POST, process_type=pt, prefix=prefix)
        if form.is_valid():
            ptrt = form.save(commit=False)
            rt = form.cleaned_data["resource_type"]
            ptrt.process_type=pt
            pattern = pt.process_pattern
            event_type = pattern.event_type_for_resource_type("work", rt)
            ptrt.event_type = event_type
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
                pattern = pt.process_pattern
                event_type = pattern.event_type_for_resource_type("in", rt)
                feature.event_type = event_type
            else:
                #todo: when will we get here? It's a hack.
                ets = EventType.objects.filter(
                    relationship="in",
                    resource_effect="-")
                event_type = ets[0]
                feature.event_type = event_type
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
        if ptrt.event_type.relationship == "work":
            form = ProcessTypeWorkForm(
                data=request.POST,
                instance=ptrt, 
                process_type=ptrt.process_type, 
                prefix=prefix)
        elif ptrt.event_type.relationship == "cite":
            form = ProcessTypeCitableForm(
                data=request.POST,
                instance=ptrt, 
                process_type=ptrt.process_type, 
                prefix=prefix)
        else:
            form = ProcessTypeInputForm(
                data=request.POST,
                instance=ptrt, 
                process_type=ptrt.process_type, 
                prefix=prefix)
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
        prefix = art.xbill_change_prefix()
        form = AgentResourceTypeForm(data=request.POST, instance=art, prefix=prefix)
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
        prefix = rt.source_create_prefix()
        form = AgentResourceTypeForm(request.POST, prefix=prefix)
        if form.is_valid():
            art = form.save(commit=False)
            art.resource_type=rt
            #todo: this is a hack
            #shd be rethought and encapsulated
            ets = EventType.objects.filter(
                related_to="agent",
                relationship="out",
                resource_effect="=")
            event_type = ets[0]
            art.event_type = event_type
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
        prefix = pt.xbill_change_prefix()
        form = ChangeProcessTypeForm(request.POST, instance=pt, prefix=prefix)
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
        prefix = rt.process_create_prefix()
        form = XbillProcessTypeForm(request.POST, prefix=prefix)
        if form.is_valid():
            data = form.cleaned_data
            pt = form.save(commit=False)
            pt.created_by=request.user
            pt.changed_by=request.user
            pt.save()
            quantity = data["quantity"]
            pattern = pt.process_pattern
            event_type = pattern.event_type_for_resource_type("out", rt)
            unit = rt.unit
            quantity = Decimal(quantity)
            ptrt = ProcessTypeResourceType(
                process_type=pt,
                resource_type=rt,
                event_type=event_type,
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
        event_type__relationship="work").order_by("due_date")
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

def json_agent(request, agent_id):
    data = serializers.serialize("json", EconomicAgent.objects.filter(id=agent_id))
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
    try:
        pattern = PatternUseCase.objects.get(use_case='cust_orders').pattern
    except PatternUseCase.DoesNotExist:
        raise ValidationError("no Customer Order ProcessPattern")
    rts = pattern.all_resource_types()
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
                                event_type=ptrt.event_type,
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
                            #import pdb; pdb.set_trace()
                            #explode_dependent_demands(commitment, request.user)
                            recursively_explode_demands(process, order, request.user, [])
                            
                        else:
                            #todo: this is certainly wrong! {but won't crash)
                            ets = EventType.objects.filter(
                                related_to="process",
                                relationship="out")
                            event_type = ets[0]
                            commitment = Commitment(
                                order=order,
                                independent_demand=order,
                                event_type=event_type,
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
                                        event_type=feature.event_type,
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
                                    explode_dependent_demands(commitment, request.user)
                                else:
                                    commitment = Commitment(
                                        independent_demand=order,
                                        event_type=feature.event_type,
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
        if process in schedule:
            return schedule
        schedule.append(process)
        #import pdb; pdb.set_trace()
        for inp in process.schedule_requirements():
            inp.depth = depth * 2
            schedule.append(inp)
            #if inp.event_type.resource_effect != "-":
            #    continue
            resource_type = inp.resource_type
            if resource_type not in visited_resources:
                #visited_resources.add(resource_type)
                pcs = resource_type.producing_commitments()
                if pcs:
                    for pc in pcs:
                        if pc.independent_demand == order:
                            schedule_commitment(pc, schedule, reqs, work, tools, visited_resources, depth+1)
                elif inp.independent_demand == order:
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
            #visited_resources.add(ct.resource_type)
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
    agent = get_agent(request)
    orders = Order.objects.filter(order_type='customer')
    rands = Order.objects.filter(order_type='rand')
    help = get_help("demand")
    return render_to_response("valueaccounting/demand.html", {
        "orders": orders,
        "rands": rands,
        "agent": agent,
        "help": help,
    }, context_instance=RequestContext(request))

def supply(request):
    mreqs = []
    #todo: needs a lot of work
    mrqs = Commitment.objects.unfinished().filter(
        event_type__resource_effect="-",
        event_type__relationship="in").order_by("resource_type__name")
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
        event_type__resource_effect="=",
        event_type__relationship="in").order_by("resource_type__name")
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
        "help": get_help("supply"),
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
    end = start + datetime.timedelta(days=7)
    #projects = assemble_schedule(start, end)   
    init = {"start_date": start, "end_date": end}
    date_form = DateSelectionForm(initial=init, data=request.POST or None)
    try:
        pattern = PatternUseCase.objects.get(use_case='todo').pattern
        todo_form = TodoForm(pattern=pattern)
    except PatternUseCase.DoesNotExist:
        todo_form = TodoForm()
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        if date_form.is_valid():
            dates = date_form.cleaned_data
            start = dates["start_date"]
            end = dates["end_date"]
    projects = assemble_schedule(start, end)
    todos = Commitment.objects.todos()
    return render_to_response("valueaccounting/work.html", {
        "agent": agent,
        "projects": projects,
        "date_form": date_form,
        "todo_form": todo_form,
        "todos": todos,
        "help": get_help("all_work"),
    }, context_instance=RequestContext(request))

def today(request):
    agent = get_agent(request)
    start = datetime.date.today()
    end = start
    #import pdb; pdb.set_trace()
    todos = Commitment.objects.todos().filter(due_date=start)
    projects = assemble_schedule(start, end)
    processes = []
    events = EconomicEvent.objects.filter(event_date=start)
    return render_to_response("valueaccounting/today.html", {
        "agent": agent,
        "projects": projects,
        "todos": todos,
        "events": events,
    }, context_instance=RequestContext(request))

def add_todo(request):
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        try:
            pattern = PatternUseCase.objects.get(use_case='todo').pattern
            form = TodoForm(data=request.POST, pattern=pattern)
        except PatternUseCase.DoesNotExist:
            form = TodoForm(request.POST)
        next = request.POST.get("next")
        agent = get_agent(request)
        et = None
        ets = EventType.objects.filter(
            relationship='todo')
        if ets:
            et = ets[0]
        if et:
            if form.is_valid():
                data = form.cleaned_data
                todo = form.save(commit=False)
                todo.to_agent=agent
                todo.event_type=et
                todo.quantity = Decimal("1")
                todo.unit_of_quantity=todo.resource_type.unit
                todo.save()
            
    return HttpResponseRedirect(next)

def create_event_from_todo(todo):
    event = EconomicEvent(
        commitment=todo,
        event_type=todo.event_type,
        event_date=datetime.date.today(),
        from_agent=todo.from_agent,
        to_agent=todo.to_agent,
        resource_type=todo.resource_type,
        project=todo.project,
        url=todo.url,
        quantity=Decimal("1"),
        unit_of_quantity=todo.resource_type.unit,
        is_contribution=True,
    )
    return event

def todo_time(request):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        todo_id = request.POST.get("todoId")
        try:
            todo = Commitment.objects.get(id=todo_id)
        except Commitment.DoesNotExist:
            todo = None
        if todo:
            hours = request.POST.get("hours")
            qty = Decimal(hours)
            event = todo.todo_event()
            if event:
                event.quantity = qty
                event.save()
            else:
                event = create_event_from_todo(todo)
                event.quantity = qty
                event.save()
    return HttpResponse("Ok", mimetype="text/plain")

def todo_description(request):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        todo_id = request.POST.get("todoId")
        try:
            todo = Commitment.objects.get(id=todo_id)
        except Commitment.DoesNotExist:
            todo = None
        if todo:
            did = request.POST.get("did")
            event = todo.todo_event()
            if event:
                event.description = did
                event.save()
            else:
                event = create_event_from_todo(todo)
                event.description = did
                event.save()
    return HttpResponse("Ok", mimetype="text/plain")

def todo_done(request, todo_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        try:
            todo = Commitment.objects.get(id=todo_id)
        except Commitment.DoesNotExist:
            todo = None
        if todo:
            todo.finished = True
            todo.save()
            event = todo.todo_event()
            if not event:
                event = create_event_from_todo(todo)
                event.save()
    next = request.POST.get("next")
    return HttpResponseRedirect(next)

def todo_mine(request, todo_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        try:
            todo = Commitment.objects.get(id=todo_id)
        except Commitment.DoesNotExist:
            todo = None
        if todo:
            agent = get_agent(request)
            todo.from_agent = agent
            todo.save()
    return HttpResponseRedirect('/%s/'
        % ('accounting/work'))

def todo_change(request, todo_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        try:
            todo = Commitment.objects.get(id=todo_id)
        except Commitment.DoesNotExist:
            todo = None
        if todo:
            prefix = todo.form_prefix()
            form = TodoForm(data=request.POST, instance=todo, prefix=prefix)
            if form.is_valid():
                todo = form.save()

    next = request.POST.get("next")
    return HttpResponseRedirect(next)

def todo_decline(request, todo_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        try:
            todo = Commitment.objects.get(id=todo_id)
        except Commitment.DoesNotExist:
            todo = None
        if todo:
            todo.from_agent=None
            todo.save()
    next = request.POST.get("next")
    return HttpResponseRedirect(next)

def todo_delete(request, todo_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        try:
            todo = Commitment.objects.get(id=todo_id)
        except Commitment.DoesNotExist:
            todo = None
        if todo:
            todo.delete()
    next = request.POST.get("next")
    return HttpResponseRedirect(next)

def start(request):
    my_work = []
    my_skillz = []
    other_wip = []
    agent = get_agent(request)
    if agent:
        my_work = Commitment.objects.unfinished().filter(
            event_type__relationship="work",
            from_agent=agent)
        skill_ids = agent.resource_types.values_list('resource_type__id', flat=True)
        my_skillz = Commitment.objects.unfinished().filter(
            from_agent=None, 
            event_type__relationship="work",
            resource_type__id__in=skill_ids)
        other_unassigned = Commitment.objects.unfinished().filter(
            from_agent=None, 
            event_type__relationship="work").exclude(resource_type__id__in=skill_ids)       
    else:
        other_unassigned = Commitment.objects.unfinished().filter(
            from_agent=None, 
            event_type__relationship="work")
    todos = Commitment.objects.todos().filter(from_agent=agent)
    init = {"from_agent": agent,}
    try:
        pattern = PatternUseCase.objects.get(use_case='todo').pattern
        todo_form = TodoForm(pattern=pattern, initial=init)
    except PatternUseCase.DoesNotExist:
        todo_form = TodoForm(initial=init)
    return render_to_response("valueaccounting/start.html", {
        "agent": agent,
        "my_work": my_work,
        "my_skillz": my_skillz,
        "other_unassigned": other_unassigned,
        "todos": todos,
        "todo_form": todo_form,
        "help": get_help("my_work"),
    }, context_instance=RequestContext(request))


def agent_stats(request, agent_id):
    agent = get_object_or_404(EconomicAgent, id=agent_id)
    scores = agent.resource_types.all()
    agents = {}
    contributions = EconomicEvent.objects.filter(is_contribution=True)
    for c in contributions:
        if c.from_agent not in agents:
            agents[c.from_agent] = Decimal("0")
        agents[c.from_agent] += c.quantity
    member_hours = []
    for key, value in agents.iteritems():
        member_hours.append((key, value))
    member_hours.sort(lambda x, y: cmp(y[1], x[1]))
    return render_to_response("valueaccounting/agent_stats.html", {
        "agent": agent,
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
            #todo: might want to change both start and end dates
            if start_date != process.start_date:
                if process.work_requirements().count() == 1:
                    process.start_date = start_date
                if process.end_date:
                    if start_date > process.end_date:
                        process.end_date = start_date
                else:
                    process.end_date = start_date
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
    #import pdb; pdb.set_trace()
    if process.process_pattern:
        pattern = process.process_pattern
        add_output_form = ProcessOutputForm(prefix='output', pattern=pattern)
        add_citation_form = ProcessCitationForm(prefix='citation', pattern=pattern)
        add_consumable_form = ProcessConsumableForm(prefix='consumable', pattern=pattern)
        add_usable_form = ProcessUsableForm(prefix='usable', pattern=pattern)
        add_work_form = WorkCommitmentForm(prefix='work', pattern=pattern)
        facet_formset = create_patterned_facet_formset(pattern, "out")
    else:
        add_output_form = ProcessOutputForm(prefix='output')
        add_citation_form = ProcessCitationForm(prefix='citation')
        add_consumable_form = ProcessConsumableForm(prefix='consumable')
        add_usable_form = ProcessUsableForm(prefix='usable')
        add_work_form = WorkCommitmentForm(prefix='work')
        facet_formset = create_facet_formset()
    cited_ids = [c.resource.id for c in process.citations()]
    resource_type_form = EconomicResourceTypeAjaxForm()
    names = EconomicResourceType.objects.values_list('name', flat=True)
    resource_names = '~'.join(names)
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
        "add_consumable_form": add_consumable_form,
        "add_usable_form": add_usable_form,
        "add_work_form": add_work_form,
        "resource_type_form": resource_type_form,
        "facet_formset": facet_formset,
        "duration": duration,
        "prev": prev,
        "was_running": was_running,
        "was_retrying": was_retrying,
        "event": event,
        "cited_ids": cited_ids,
        "resource_names": resource_names,
        "help": get_help("labnotes"),
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
                pattern = process.process_pattern
                event_type = pattern.event_type_for_resource_type("out", rt)
                ct.event_type = event_type
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

def new_process_input(request, commitment_id, slot):
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
        pattern = commitment.process.process_pattern
        if slot == "c":
            form = ProcessConsumableForm(data=request.POST, pattern=pattern, prefix='consumable')
            rel = "consume"
        elif slot == "u":
            form = ProcessUsableForm(data=request.POST, pattern=pattern, prefix='usable')
            rel = "use"
        if form.is_valid():
            input_data = form.cleaned_data
            qty = input_data["quantity"]
            if qty:
                process = commitment.process
                demand = process.independent_demand()
                ct = form.save(commit=False)
                rt = input_data["resource_type"]
                pattern = process.process_pattern
                event_type = pattern.event_type_for_resource_type(rel, rt)
                ct.event_type = event_type
                ct.process = process
                ct.independent_demand = demand
                ct.due_date = process.start_date
                ct.created_by = request.user
                ptrt = ct.resource_type.main_producing_process_type_relationship()
                if ptrt:
                    ct.project = ptrt.process_type.project
                ct.save()
                #todo: this is used in labnotes; shd it explode?
                #explode_dependent_demands(ct, request.user)                
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
            rt = input_data["resource_type"]
            pattern = process.process_pattern
            event_type = pattern.event_type_for_resource_type("cite", rt)
            agent = get_agent(request)
            ct = Commitment(
                process=process,
                #from_agent=agent,
                independent_demand=demand,
                event_type=event_type,
                due_date=process.start_date,
                resource_type=rt,
                project=process.project,
                quantity=quantity,
                unit_of_quantity=rt.directional_unit("cite"),
                created_by=request.user,
            )
            ct.save()
                
    if reload == 'pastwork':
        return HttpResponseRedirect('/%s/%s/%s/%s/%s/'
            % ('accounting/pastwork-reload', commitment.id, event_id, was_running, was_retrying))
    else:
        return HttpResponseRedirect('/%s/%s/%s/%s/'
            % ('accounting/labnotes-reload', commitment.id, was_running, was_retrying))

def new_process_worker(request, commitment_id):
    commitment = get_object_or_404(Commitment, pk=commitment_id)
    was_running = request.POST["wasRunning"] or 0
    was_retrying = request.POST["wasRetrying"] or 0
    #comes from past_work
    event_date = request.POST.get("workDate")
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
        form = WorkCommitmentForm(data=request.POST, prefix='work')
        if form.is_valid():
            input_data = form.cleaned_data
            process = commitment.process
            demand = process.independent_demand()
            rt = input_data["resource_type"]
            pattern = process.process_pattern
            event_type = pattern.event_type_for_resource_type("work", rt)
            ct = form.save(commit=False)
            ct.process=process
            ct.independent_demand=demand
            ct.event_type=event_type
            ct.due_date=process.end_date
            ct.resource_type=rt
            ct.project=process.project
            ct.unit_of_quantity=rt.directional_unit("use")
            ct.created_by=request.user
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

def change_event_date(request):
    #import pdb; pdb.set_trace()
    event_id = request.POST.get("eventId")
    event = get_object_or_404(EconomicEvent, pk=event_id)
    form = EventChangeDateForm(data=request.POST, instance=event, prefix=event_id)
    if form.is_valid():
        data = form.cleaned_data
        event = form.save()

    return HttpResponse("Ok", mimetype="text/plain")

def change_event_qty(request):
    #import pdb; pdb.set_trace()
    event_id = request.POST.get("eventId")
    event = get_object_or_404(EconomicEvent, pk=event_id)
    form = EventChangeQuantityForm(data=request.POST, instance=event, prefix=event_id)
    if form.is_valid():
        data = form.cleaned_data
        event = form.save()

    return HttpResponse("Ok", mimetype="text/plain")

def change_event(request, event_id):
    event = get_object_or_404(EconomicEvent, pk=event_id)
    page = request.GET.get("page")
    event_form = WorkContributionChangeForm(instance=event, data=request.POST or None)
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        page = request.POST.get("page")
        if event_form.is_valid():
            event = event_form.save(commit=False)
            event.changed_by = request.user
            event.save()
        agent = event.from_agent
        if page:
            return HttpResponseRedirect('/%s/%s/?page=%s'
                % ('accounting/contributionhistory', agent.id, page))
        else:
            return HttpResponseRedirect('/%s/%s/'
                % ('accounting/contributionhistory', agent.id))
    return render_to_response("valueaccounting/change_event.html", {
        "event_form": event_form,
        "page": page,
    }, context_instance=RequestContext(request)) 
        
def delete_event(request, event_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        event = get_object_or_404(EconomicEvent, pk=event_id)
        agent = event.from_agent
        event.delete()        
        next = request.POST.get("next")
        if next == "resource":
            resource_id = request.POST.get("resource_id")
            return HttpResponseRedirect('/%s/%s/'
                % ('accounting/resource', resource_id))
        elif next == "contributions":
            page = request.POST.get("page")
            
            if page:
                return HttpResponseRedirect('/%s/%s/?page=%s'
                    % ('accounting/contributionhistory', agent.id, page))
            else:
                return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/contributionhistory', agent.id))

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

    if process.process_pattern:
        pattern = process.process_pattern
        add_output_form = ProcessOutputForm(prefix='output', pattern=pattern)
        add_citation_form = ProcessCitationForm(prefix='citation', pattern=pattern)
        add_consumable_form = ProcessConsumableForm(prefix='consumable', pattern=pattern)
        add_usable_form = ProcessUsableForm(prefix='usable', pattern=pattern)
        add_work_form = WorkCommitmentForm(prefix='work', pattern=pattern)
        facet_formset = create_patterned_facet_formset(pattern, "out")
    else:
        add_output_form = ProcessOutputForm(prefix='output')
        add_citation_form = ProcessCitationForm(prefix='citation')
        add_consumable_form = ProcessConsumableForm(prefix='consumable')
        add_usable_form = ProcessUsableForm(prefix='usable')
        add_work_form = WorkCommitmentForm(prefix='work')
        facet_formset = create_facet_formset()
    cited_ids = [c.resource.id for c in process.citations()]
    resource_type_form = EconomicResourceTypeAjaxForm()
    names = EconomicResourceType.objects.values_list('name', flat=True)
    resource_names = '~'.join(names)
    return {
        "commitment": commitment,
        "process": process,
        "wb_form": wb_form,
        "others_working": others_working,
        "other_work_reqs": other_work_reqs,
        "failure_form": failure_form,
        "add_output_form": add_output_form,
        "add_citation_form": add_citation_form,
        "add_consumable_form": add_consumable_form,
        "add_usable_form": add_usable_form,
        "add_work_form": add_work_form,
        "resource_type_form": resource_type_form,
        "facet_formset": facet_formset,
        "duration": duration,
        "prev": prev,
        "was_running": was_running,
        "was_retrying": was_retrying,
        "event": event,
        "event_date": event_date,
        "cited_ids": cited_ids,
        "resource_names": resource_names,
        "help": get_help("labnotes"),
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
            #todo: if the past work logging form becomes accessible other ways,
            # existing events will need to be retrieved when the date is entered.
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
    agent = get_agent(request)
    process = get_object_or_404(Process, id=process_id)
    labnotes = False
    if process.work_events():
        labnotes = True
    cited_ids = [c.resource.id for c in process.citations()]
    return render_to_response("valueaccounting/process.html", {
        "process": process,
        "labnotes": labnotes,
        "cited_ids": cited_ids,
        "agent": agent,
        "help": get_help("process"),
    }, context_instance=RequestContext(request))

def labnotes_history(request):
    agent = get_agent(request)
    procs = Process.objects.all().order_by("-start_date")
    candidates = [p for p in procs if p.work_events()]
    process_list = []
    for p in candidates:
        for e in p.work_requirements():
            if e.description:
                if p not in process_list:
                    process_list.append(p)
                    
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
        
    return render_to_response("valueaccounting/labnotes_history.html", {
        "processes": processes,
        "photo_size": (128, 128),
        "agent": agent,
    }, context_instance=RequestContext(request))

def todo_history(request):
    #import pdb; pdb.set_trace()
    todo_list = Commitment.objects.finished_todos().order_by('-due_date',)
                   
    paginator = Paginator(todo_list, 25)
    page = request.GET.get('page')
    try:
        todos = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        todos = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        todos = paginator.page(paginator.num_pages)
        
    return render_to_response("valueaccounting/todo_history.html", {
        "todos": todos,
    }, context_instance=RequestContext(request))


def resource(request, resource_id):
    resource = get_object_or_404(EconomicResource, id=resource_id)
    agent = get_agent(request)
    process_add_form = None
    agent_form = None
    work_form = None
    cite_form = None
    process = None
    pattern = None
    #import pdb; pdb.set_trace()
    if resource.producing_events(): 
        process = resource.producing_events()[0].process
        pattern = None
        if process:
            pattern = process.process_pattern 
        work_form = SimpleWorkForm(prefix='work', pattern=pattern)
        agent_form = AgentContributorSelectionForm()
        cite_form = SelectCitationResourceForm(prefix='cite', pattern=pattern)
    else:
        form_data = {'name': 'Create ' + resource.identifier, 'start_date': resource.created_date, 'end_date': resource.created_date}
        process_add_form = AddProcessFromResourceForm(form_data)    
    
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        process_save = request.POST.get("process-save")
        cite_save = request.POST.get("cite-save")
        work_save = request.POST.get("work-save")
        if process_save:
            process_add_form = AddProcessFromResourceForm(data=request.POST)
            if process_add_form.is_valid():
                process = process_add_form.save(commit=False)
                process.started = process.start_date
                process.finished = True
                process.created_by = request.user
                process.save() 
                event = EconomicEvent()
                event.project = process.project
                event.event_date = process.end_date
                event.event_type = process.process_pattern.event_type_for_resource_type("out", resource.resource_type)
                event.process = process
                event.resource_type = resource.resource_type 
                event.quantity = resource.quantity 
                event.unit_of_quantity = resource.unit_of_quantity 
                event.resource = resource
                event.created_by = request.user
                event.save()
                #pattern = process.process_pattern 
                #work_form = SimpleWorkForm(prefix='work', pattern=pattern)
                #agent_form = AgentContributorSelectionForm()
                #cite_form = SelectCitationResourceForm(prefix='cite', pattern=pattern)
                return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/resource', resource.id))
        elif cite_save:
            if request.POST['cite-resource']:
                cite_form = SelectCitationResourceForm(data=request.POST, prefix='cite', pattern=pattern)
                cr = EconomicResource.objects.get(id=int(request.POST['cite-resource']))
                citation_event = EconomicEvent()
                citation_event.event_type = pattern.event_type_for_resource_type("cite", cr.resource_type)
                citation_event.event_date = process.end_date
                citation_event.process = process
                citation_event.project = process.project
                citation_event.resource = cr
                citation_event.resource_type = cr.resource_type
                citation_event.quantity = 1
                citation_event.unit_of_quantity = citation_event.resource_type.directional_unit("cite")  
                citation_event.created_by = request.user
                citation_event.save()
                #work_form = SimpleWorkForm(prefix='work', pattern=pattern)
                #agent_form = AgentContributorSelectionForm()
                #cite_form = SelectCitationResourceForm(prefix='cite', pattern=pattern)
                return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/resource', resource.id))
        elif work_save:
            work_form = SimpleWorkForm(data=request.POST, prefix='work', pattern=pattern)
            if work_form.is_valid():
                agent_form = AgentContributorSelectionForm(data=request.POST)
                work_event = work_form.save(commit=False)
                work_event.event_type = pattern.event_type_for_resource_type("work", work_event.resource_type)
                work_event.event_date = process.end_date
                work_event.process = process
                work_event.project = process.project
                work_event.is_contribution = True
                work_event.unit_of_quantity = work_event.resource_type.directional_unit("use")  
                work_event.from_agent = EconomicAgent.objects.get(id=int(request.POST['selected_agent']))
                work_event.created_by = request.user
                work_event.save()
                #work_form = SimpleWorkForm(prefix='work', pattern=pattern)
                #agent_form = AgentContributorSelectionForm()
                #cite_form = SelectCitationResourceForm(prefix='cite', pattern=pattern)
                return HttpResponseRedirect('/%s/%s/'
                    % ('accounting/resource', resource.id))

    return render_to_response("valueaccounting/resource.html", {
        "resource": resource,
        "photo_size": (128, 128),
        "process_add_form": process_add_form,
        "cite_form": cite_form,
        "work_form": work_form,
        "agent_form": agent_form,
        "agent": agent,
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
    consumed = process.inputs_consumed_by_agent(agent)
    used = process.inputs_used_by_agent(agent)
    citations = process.citations_by_agent(agent)
    return {
        "commitment": commitment,
        "author": author,
        "process": process,
        "work_events": work_events,
        "outputs": outputs,
        "failures": failures,
        "consumed": consumed,
        "used": used,
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
    if quantity:
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

#todo: obsolete
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
                        #rel = 
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
                        #rel = 
                        ct.relationship = rel
                        ct.event_type = rel.event_type
                        ct.process = process
                        ct.independent_demand = demand
                        ct.due_date = process.start_date
                        ct.created_by = request.user
                        rt = ct.resource_type
                        ptrt = rt.main_producing_process_type_relationship()
                        ct.save()
                        explode_dependent_demands(ct, request.user)
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

#todo: obsolete
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
                        #rel = 
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
                        #rel = 
                        ct.relationship = rel
                        ct.event_type = rel.event_type
                        ct.process = process
                        ct.independent_demand = demand
                        ct.due_date = process.start_date
                        ct.created_by = request.user
                        rt = ct.resource_type
                        ptrt = rt.main_producing_process_type_relationship()
                        ct.save()
                        explode_dependent_demands(ct, request.user)
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


class ProcessOutputFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.pattern = kwargs.pop('pattern', None)
        super(ProcessOutputFormSet, self).__init__(*args, **kwargs)

    def _construct_forms(self): 
        self.forms = []
        #import pdb; pdb.set_trace()
        for i in xrange(self.total_form_count()):
            self.forms.append(self._construct_form(i, pattern=self.pattern))


class ProcessInputFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.pattern = kwargs.pop('pattern', None)
        super(ProcessInputFormSet, self).__init__(*args, **kwargs)

    def _construct_forms(self): 
        self.forms = []
        #import pdb; pdb.set_trace()
        for i in xrange(self.total_form_count()):
            self.forms.append(self._construct_form(i, pattern=self.pattern))


class ProcessCitationFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.pattern = kwargs.pop('pattern', None)
        super(ProcessCitationFormSet, self).__init__(*args, **kwargs)

    def _construct_forms(self): 
        self.forms = []
        #import pdb; pdb.set_trace()
        for i in xrange(self.total_form_count()):
            self.forms.append(self._construct_form(i, pattern=self.pattern))


class ProcessWorkFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.pattern = kwargs.pop('pattern', None)
        super(ProcessWorkFormSet, self).__init__(*args, **kwargs)

    def _construct_forms(self): 
        self.forms = []
        #import pdb; pdb.set_trace()
        for i in xrange(self.total_form_count()):
            self.forms.append(self._construct_form(i, pattern=self.pattern))


@login_required
def change_process(request, process_id):
    process = get_object_or_404(Process, id=process_id)
    demand = process.independent_demand()
    existing_demand = demand
    if demand:
        if demand.order_type != "holder":
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
    else:
        demand_form = DemandSelectionForm(data=request.POST or None)    
        rand_form = RandOrderForm(data=request.POST or None)
    process_form = ProcessForm(instance=process, data=request.POST or None)
    pattern = None
    if process.process_pattern:
        pattern = process.process_pattern
    OutputFormSet = modelformset_factory(
        Commitment,
        form=ProcessOutputForm,
        formset=ProcessOutputFormSet,
        can_delete=True,
        extra=1,
        )
    output_formset = OutputFormSet(
        queryset=process.outgoing_commitments(),
        data=request.POST or None,
        prefix='output',
        pattern=pattern)
    CitationFormSet = modelformset_factory(
        Commitment,
        form=ProcessCitationCommitmentForm,
        formset=ProcessCitationFormSet,
        can_delete=True,
        extra=2,
        )
    citation_formset = CitationFormSet(
        queryset=process.citation_requirements(),
        data=request.POST or None,
        prefix='citation',
        pattern=pattern)
    WorkFormSet = modelformset_factory(
        model=Commitment,
        form=ProcessWorkForm,
        formset=ProcessWorkFormSet,
        can_delete=True,
        extra=2,
        )
    work_formset = WorkFormSet(
        queryset=process.work_requirements(),
        data=request.POST or None,
        prefix='work',
        pattern=pattern)
    ConsumableFormSet = modelformset_factory(
        Commitment,
        form=ProcessConsumableForm,
        formset=ProcessInputFormSet,
        can_delete=True,
        extra=2,
        )
    consumable_formset = ConsumableFormSet(
        queryset=process.consumed_input_requirements(),
        data=request.POST or None,
        prefix='consumable',
        pattern=pattern)
    UsableFormSet = modelformset_factory(
        Commitment,
        form=ProcessUsableForm,
        formset=ProcessInputFormSet,
        can_delete=True,
        extra=2,
        )
    usable_formset = UsableFormSet(
        queryset=process.used_input_requirements(),
        data=request.POST or None,
        prefix='usable',
        pattern=pattern)
        
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        keep_going = request.POST.get("keep-going")
        just_save = request.POST.get("save")
        if process_form.is_valid():
            process_data = process_form.cleaned_data
            process = process_form.save(commit=False)
            process.changed_by=request.user
            process.save()
            pattern = process.process_pattern
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
                            event_type = pattern.event_type_for_resource_type("out", rt)
                            ct.event_type = event_type
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
                                        event_type = pattern.event_type_for_resource_type("cite", rt)
                                        ct.event_type = event_type
                                        unit = rt.unit
                                        ct.unit_of_quantity = unit
                                        ct.changed_by = request.user
                                else:
                                    ct.process = process
                                    ct.created_by = request.user
                                    event_type = pattern.event_type_for_resource_type("cite", rt)
                                    ct.event_type = event_type
                                    unit = rt.unit
                                    ct.unit_of_quantity = unit
                                ct.save()
                        elif ct_from_id:
                            ct = form.save()
                            ct.delete() 

            for form in work_formset.forms:
                #import pdb; pdb.set_trace()
                if form.is_valid():
                    work_data = form.cleaned_data
                    if work_data:
                        hours = work_data["quantity"]
                        ct_from_id = work_data["id"]
                        if hours:
                            rt = work_data["resource_type"]
                            if rt:
                                ct = form.save(commit=False)
                                ct.independent_demand = demand
                                ct.project = process.project
                                ct.due_date = process.end_date
                                if ct_from_id:
                                    old_ct = Commitment.objects.get(id=ct_from_id.id)
                                    old_rt = old_ct.resource_type
                                    if not old_rt == rt:
                                        event_type = pattern.event_type_for_resource_type("work", rt)
                                        ct.event_type = event_type
                                        unit = rt.unit
                                        ct.unit_of_quantity = unit
                                        ct.changed_by = request.user
                                else:
                                    ct.process = process
                                    ct.created_by = request.user
                                    event_type = pattern.event_type_for_resource_type("work", rt)
                                    ct.event_type = event_type
                                    unit = rt.unit
                                    ct.unit_of_quantity = unit
                                ct.save()
                        elif ct_from_id:
                            ct = form.save()
                            ct.delete() 

            for form in consumable_formset.forms:
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
                            visited_resources = set()
                            collect_lower_trash(ct, trash, visited_resources)
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
                                        visited_resources = set()
                                        collect_trash(ex_ct, trash, visited_resources)
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
                                        propagate_changes(pc, delta, existing_demand, demand, [])
                                    else:
                                        propagate_qty_change(pc, delta, []) 
                            else:
                                if demand != existing_demand:
                                    delta = Decimal("0")
                                    for pc in propagators:
                                        propagate_changes(pc, delta, existing_demand, demand, [])                    
                            ct.changed_by = request.user
                            rt = input_data["resource_type"]
                            event_type = pattern.event_type_for_resource_type("consume", rt)
                            ct.event_type = event_type
                        else:
                            explode = True
                            rt = input_data["resource_type"]
                            event_type = pattern.event_type_for_resource_type("consume", rt)
                            ct.event_type = event_type
                            ct.process = process
                            ct.independent_demand = demand
                            ct.due_date = process.start_date
                            ct.created_by = request.user
                            ptrt = ct.resource_type.main_producing_process_type_relationship()
                            if ptrt:
                                ct.project = ptrt.process_type.project
                        ct.save()
                        if explode:
                            #todo: use new commitment.generate_producing_process(request.user, explode=True)
                            explode_dependent_demands(ct, request.user)
            for form in usable_formset.forms:
                #import pdb; pdb.set_trace()
                if form.is_valid():
                    #probly not needed for usables
                    explode = False
                    input_data = form.cleaned_data
                    qty = input_data["quantity"]
                    ct_from_id = input_data["id"]
                    #import pdb; pdb.set_trace()
                    if not qty:
                        if ct_from_id:
                            ct = form.save()
                            #probly not needed for usables
                            trash = []
                            visited_resources = set()
                            collect_lower_trash(ct, trash, visited_resources)
                            for proc in trash:
                                if proc.outgoing_commitments().count() <= 1:
                                    proc.delete()
                            #but ct.delete is needed
                            ct.delete()
                    else:
                        ct = form.save(commit=False)
                        ct.independent_demand = demand
                        if ct_from_id:
                            producers = ct.resource_type.producing_commitments()
                            propagators = []
                            old_ct = Commitment.objects.get(id=ct_from_id.id)
                            old_rt = old_ct.resource_type
                            #probly not needed for usables
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
                                #todo: needed for usables?
                                for ex_ct in old_rt.producing_commitments():
                                    if demand == ex_ct.independent_demand:
                                        trash = []
                                        visited_resources = set()
                                        collect_trash(ex_ct, trash, visited_resources)
                                        for proc in trash:
                                            #todo: feeder process with >1 outputs 
                                            # shd find the correct output to delete
                                            # and keep the others
                                            if proc.outgoing_commitments().count() <= 1:
                                                proc.delete()
                                explode = True                                 
                            elif qty != old_ct.quantity:
                                delta = qty - old_ct.quantity
                                #probly not needed for usables
                                for pc in propagators:
                                    if demand != existing_demand:
                                        propagate_changes(pc, delta, existing_demand, demand, [])
                                    else:
                                        propagate_qty_change(pc, delta, []) 
                            else:
                                #probly not needed for usables
                                if demand != existing_demand:
                                    delta = Decimal("0")
                                    for pc in propagators:
                                        propagate_changes(pc, delta, existing_demand, demand, [])                    
                            ct.changed_by = request.user
                            rt = input_data["resource_type"]
                            event_type = pattern.event_type_for_resource_type("use", rt)
                            ct.event_type = event_type
                        else:
                            explode = True
                            rt = input_data["resource_type"]
                            event_type = pattern.event_type_for_resource_type("use", rt)
                            ct.event_type = event_type
                            ct.process = process
                            ct.independent_demand = demand
                            ct.due_date = process.start_date
                            ct.created_by = request.user
                            ptrt = ct.resource_type.main_producing_process_type_relationship()
                            if ptrt:
                                ct.project = ptrt.process_type.project
                        ct.save()
                        #probly not needed for usables
                        #if explode:
                        #    explode_dependent_demands(ct, request.user)

                
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
        "consumable_formset": consumable_formset,
        "usable_formset": usable_formset,
        "work_formset": work_formset,
    }, context_instance=RequestContext(request))

#todo: soon to be obsolete
def explode_dependent_demands(commitment, user):
    """This method assumes an input commitment"""
    
    #import pdb; pdb.set_trace()
    qty_to_explode = commitment.net()
    if qty_to_explode:
        rt = commitment.resource_type
        ptrt = rt.main_producing_process_type_relationship()
        demand = commitment.independent_demand
        if ptrt:
            pt = ptrt.process_type
            start_date = commitment.due_date - datetime.timedelta(minutes=pt.estimated_duration)
            feeder_process = Process(
                name=pt.name,
                process_type=pt,
                process_pattern=pt.process_pattern,
                project=pt.project,
                url=pt.url,
                end_date=commitment.due_date,
                start_date=start_date,
                created_by=user,
            )
            feeder_process.save()

            output_commitment = Commitment(
                independent_demand=demand,
                event_type=ptrt.event_type,
                due_date=commitment.due_date,
                resource_type=rt,
                process=feeder_process,
                project=pt.project,
                quantity=qty_to_explode,
                unit_of_quantity=rt.unit,
                description=ptrt.description,
                created_by=user,
            )
            output_commitment.save()
            recursively_explode_demands(feeder_process, demand, user, [])
    
def propagate_qty_change(commitment, delta, visited):
    #import pdb; pdb.set_trace()
    process = commitment.process
    if process not in visited:
        visited.append(process)
        for ic in process.incoming_commitments():
            if ic.event_type.relationship != "cite":
                ratio = ic.quantity / commitment.quantity 
                new_delta = (delta * ratio).quantize(Decimal('.01'), rounding=ROUND_UP)
                ic.quantity += new_delta
                ic.save()
                rt = ic.resource_type
                demand = ic.independent_demand
                for pc in rt.producing_commitments():
                    if pc.independent_demand == demand:
                        propagate_qty_change(pc, new_delta, visited)
    commitment.quantity += delta
    commitment.save()  

def propagate_changes(commitment, delta, old_demand, new_demand, visited):
    #import pdb; pdb.set_trace()
    process = commitment.process
    if process not in visited:
        visited.append(process)
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
                    propagate_changes(pc, new_delta, old_demand, new_demand, visited)
    commitment.quantity += delta
    commitment.independent_demand = new_demand
    commitment.save()    

#todo: obsolete?
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
                pattern = process.process_pattern
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
                            event_type = pattern.event_type_for_resource_type("out", rt)
                            ct.event_type = event_type
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
                            explode_dependent_demands(ct, request.user)
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

#todo: obsolete
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
                            #rel = 
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
                            #rel = 
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
                            explode_dependent_demands(ct, request.user)
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


#todo: obsolete?
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
                pattern = process.process_pattern
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
                                event_type = pattern.event_type_for_resource_type("out", rt)
                                ct.event_type = event_type
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
                                visited_resources = set()
                                collect_lower_trash(ct, trash, visited_resources)
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
                                            visited_resources = set()
                                            collect_trash(ex_ct, trash, visited_resources)
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
                                    #import pdb; pdb.set_trace()
                                    delta = qty - old_ct.quantity
                                    for pc in ct.resource_type.producing_commitments():
                                        if pc.independent_demand == demand:
                                            propagate_qty_change(pc, delta, [])                                
                                ct.changed_by = request.user
                                rt = input_data["resource_type"]
                                event_type = pattern.event_type_for_resource_type("in", rt)
                                ct.event_type = rel.event_type
                            else:
                                explode = True
                                rt = input_data["resource_type"]
                                event_type = pattern.event_type_for_resource_type("in", rt)
                                ct.event_type = event_type
                                ct.independent_demand = rand
                                ct.process = process
                                ct.due_date = process.start_date
                                ct.created_by = request.user
                                ptrt = ct.resource_type.main_producing_process_type_relationship()
                                if ptrt:
                                    ct.project = ptrt.process_type.project
                            ct.save()
                            if explode:
                                explode_dependent_demands(ct, request.user)
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


class ResourceType_EventType(object):
    def __init__(self, resource_type, event_type):
        self.resource_type = resource_type
        self.event_type = event_type

@login_required
def process_selections(request, rand=0):
    #import pdb; pdb.set_trace()
    slots = []
    resource_types = []
    selected_pattern = None
    selected_project = None
    pattern_form = PatternProdSelectionForm()
    #import pdb; pdb.set_trace()
    project_form = ProjectSelectionForm()
    init = {"start_date": datetime.date.today(), "end_date": datetime.date.today()}
    date_form = DateSelectionForm(data=request.POST or None)
    demand_form = DemandSelectionForm(data=request.POST or None)
    if request.method == "POST":
        input_resource_types = []
        input_process_types = []
        done_process = request.POST.get("create-process")
        edit_process = request.POST.get("edit-process")
        labnotes = request.POST.get("labnotes")
        past = request.POST.get("past")
        get_related = request.POST.get("get-related")
        if get_related:
            #import pdb; pdb.set_trace()
            selected_pattern = ProcessPattern.objects.get(id=request.POST.get("pattern"))
            selected_project = Project.objects.get(id=request.POST.get("project"))
            if selected_pattern:
                slots = selected_pattern.event_types()
                for slot in slots:
                    slot.resource_types = selected_pattern.get_resource_types(slot)
            date_form = DateSelectionForm(initial=init)
        else:
            #import pdb; pdb.set_trace()
            rp = request.POST
            today = datetime.date.today()
            if date_form.is_valid():
                start_date = date_form.cleaned_data["start_date"]
                end_date = date_form.cleaned_data["end_date"]
            else:
                start_date = today
                end_date = today
            demand = None
            if demand_form.is_valid():
                demand = demand_form.cleaned_data["demand"]                
            produced_rts = []
            cited_rts = []
            consumed_rts = []
            used_rts = []
            work_rts = []
            for key, value in dict(rp).iteritems():
                if "selected-project" in key:
                    project_id = key.split("~")[1]
                    selected_project = Project.objects.get(id=project_id)
                    continue
                if "selected-pattern" in key:
                    pattern_id = key.split("~")[1]
                    selected_pattern = ProcessPattern.objects.get(id=pattern_id)
                    continue
                et = None
                action = ""
                try:
                    #import pdb; pdb.set_trace()
                    label = key.split("~")[0]
                    et = EventType.objects.get(label=label)
                except EventType.DoesNotExist:
                    pass
                if et:
                    if et.relationship == "in":
                        if et.resource_effect == "=":
                            action = "uses"
                        else:
                            action = "consumes"
                    else:
                        action = et.relationship
                if action == "consumes":
                    consumed_id = int(value[0])
                    consumed_rt = EconomicResourceType.objects.get(id=consumed_id)
                    consumed_rts.append(consumed_rt)
                    continue
                if action == "uses":
                    used_id = int(value[0])
                    used_rt = EconomicResourceType.objects.get(id=used_id)
                    used_rts.append(used_rt)
                    continue
                if action == "cite":
                    cited_id = int(value[0])
                    cited_rt = EconomicResourceType.objects.get(id=cited_id)
                    cited_rts.append(cited_rt)
                    continue
                if action == "out":
                    produced_id = int(value[0])
                    produced_rt = EconomicResourceType.objects.get(id=produced_id)
                    produced_rts.append(produced_rt)
                    continue
                if action == "work":
                    work_id = int(value[0])
                    work_rt = EconomicResourceType.objects.get(id=work_id)
                    work_rts.append(work_rt)
                    continue

            if rand: 
                if not demand:
                    demand = Order(
                        order_type="rand",
                        order_date=today,
                        due_date=end_date,
                        created_by=request.user)
                    demand.save()

            name = "Make something"
            if produced_rts:
                name = " ".join([
                    "Make",
                    produced_rts[0].name,
                ])

            process = Process(
                name=name,
                end_date=end_date,
                start_date=start_date,
                process_pattern=selected_pattern,
                created_by=request.user,
                project=selected_project
            )
            process.save()
        
            #import pdb; pdb.set_trace()      
            for rt in produced_rts:
                resource_types.append(rt)
                et = selected_pattern.event_type_for_resource_type("out", rt)
                if et:
                    commitment = process.add_commitment(
                        resource_type= rt,
                        demand=demand,
                        quantity=Decimal("1"),
                        event_type=et,
                        unit=rt.unit,
                        user=request.user)
                    if rand:
                        #use recipe
                        pt = rt.main_producing_process_type()
                        process.process_type=pt
                        process.save()
                        if pt:
                            for xrt in pt.cited_resource_types():
                                if xrt not in resource_types:
                                    resource_types.append(xrt)
                            for xrt in pt.used_resource_types():
                                if xrt not in resource_types:
                                    resource_types.append(xrt)
                            for xrt in pt.consumed_resource_types():
                                if xrt not in resource_types:
                                    resource_types.append(xrt)
                            for xrt in pt.work_resource_types():
                                if xrt not in resource_types:
                                    resource_types.append(xrt)
                        process.explode_demands(demand, request.user, [])
            for rt in cited_rts:
                et = selected_pattern.event_type_for_resource_type("cite", rt)
                if et:
                    """
                    commitment = Commitment(
                        process=process,
                        independent_demand=demand,
                        project=process.project,
                        event_type=et,
                        start_date=start_date,
                        due_date=end_date,
                        resource_type=rt,
                        quantity=Decimal("1"),
                        unit_of_quantity=rt.unit,
                        created_by=request.user,
                    )
                    commitment.save()
                    """
                    commitment = process.add_commitment(
                        resource_type= rt,
                        demand=demand,
                        quantity=Decimal("1"),
                        event_type=et,
                        unit=rt.unit,
                        user=request.user)
            for rt in used_rts:
                if rt not in resource_types:
                    resource_types.append(rt)
                    et = selected_pattern.event_type_for_resource_type("use", rt)
                    if et:
                        """
                        commitment = Commitment(
                            process=process,
                            independent_demand=demand,
                            project=process.project,
                            event_type=et,
                            start_date=start_date,
                            due_date=end_date,
                            resource_type=rt,
                            quantity=Decimal("1"),
                            unit_of_quantity=rt.unit,
                            created_by=request.user,
                        )
                        commitment.save()
                        """
                        commitment = process.add_commitment(
                            resource_type= rt,
                            demand=demand,
                            quantity=Decimal("1"),
                            event_type=et,
                            unit=rt.unit,
                            user=request.user)
                        
            for rt in consumed_rts:
                if rt not in resource_types:
                    resource_types.append(rt)
                    et = selected_pattern.event_type_for_resource_type("consume", rt)
                    if et:
                        """
                        commitment = Commitment(
                            process=process,
                            independent_demand=demand,
                            project=process.project,
                            event_type=et,
                            start_date=start_date,
                            due_date=end_date,
                            resource_type=rt,
                            quantity=Decimal("1"),
                            unit_of_quantity=rt.unit,
                            created_by=request.user,
                        )
                        commitment.save()
                        """
                        commitment = process.add_commitment(
                            resource_type= rt,
                            demand=demand,
                            quantity=Decimal("1"),
                            event_type=et,
                            unit=rt.unit,
                            user=request.user)
                            
            for rt in work_rts:
                #import pdb; pdb.set_trace()
                agent = None
                if past or labnotes:
                    agent = get_agent(request)
                et = selected_pattern.event_type_for_resource_type("work", rt)
                if et:
                    """
                    work_commitment = Commitment(
                        process=process,
                        independent_demand=demand,
                        project=process.project,
                        event_type=et,
                        from_agent=agent,
                        start_date=start_date,
                        due_date=end_date,
                        resource_type=rt,
                        quantity=Decimal("1"),
                        unit_of_quantity=rt.unit,
                        created_by=request.user,
                    )
                    work_commitment.save()
                    """
                    work_commitment = process.add_commitment(
                        resource_type= rt,
                        demand=demand,
                        quantity=Decimal("1"),
                        event_type=et,
                        unit=rt.unit,
                        from_agent=agent,
                        user=request.user)

            if done_process: 
                return HttpResponseRedirect('/%s/'
                    % ('accounting/process-selections'))                 
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
        "slots": slots,
        "selected_pattern": selected_pattern,
        "selected_project": selected_project,
        "project_form": project_form,
        "pattern_form": pattern_form,
        "date_form": date_form,
        "demand_form": demand_form,
        "rand": rand,
        "help": get_help("process_selections"),
    }, context_instance=RequestContext(request))


@login_required
def resource_facet_table(request):
    headings = ["Resource Type"]
    rows = []
    facets = Facet.objects.all()
    for facet in facets:
        headings.append(facet)
    for rt in EconomicResourceType.objects.all():
        row = [rt, ]
        for i in range(0, facets.count()):
            row.append(" ")
        for rf in rt.facets.all():
            cell = headings.index(rf.facet_value.facet)
            row[cell] = rf
        rows.append(row)     
    return render_to_response("valueaccounting/resource_facets.html", {
        "headings": headings,
        "rows": rows,
    }, context_instance=RequestContext(request))

@login_required
def change_resource_facet_value(request):
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        #resource_type_label = request.POST.get("resourceType")
        #rt_name = resource_type_label.split("-", 1)[1].lstrip()
        rt_name = request.POST.get("resourceType")
        facet_name = request.POST.get("facet")
        value = request.POST.get("facetValue")
        rt = EconomicResourceType.objects.get(name=rt_name)
        facet = Facet.objects.get(name=facet_name)
        facet_value = None
        if value:
            facet_value = FacetValue.objects.get(facet=facet, value=value)
        rtfv = None
        try:
            rtfv = ResourceTypeFacetValue.objects.get(
                resource_type=rt,
                facet_value__facet=facet)
        except ResourceTypeFacetValue.DoesNotExist:
            pass
        if rtfv:
            if rtfv.facet_value != facet_value:
                rtfv.delete()
                rtfv = None
        if not rtfv:
            if value:
                rtfv = ResourceTypeFacetValue(
                    resource_type=rt,
                    facet_value=facet_value)
                rtfv.save()

    return HttpResponse("Ok", mimetype="text/plain")

def create_facet_formset(data=None):
    RtfvFormSet = formset_factory(ResourceTypeFacetValueForm, extra=0)
    init = []
    facets = Facet.objects.all()
    for facet in facets:
        d = {"facet_id": facet.id,}
        init.append(d)
    formset = RtfvFormSet(initial=init, data=data)
    for form in formset:
        id = int(form["facet_id"].value())
        facet = Facet.objects.get(id=id)
        form.facet_name = facet.name
        fvs = facet.values.all()
        choices = [('', '----------')] + [(fv.id, fv.value) for fv in fvs]
        form.fields["value"].choices = choices
    return formset

def create_patterned_facet_formset(pattern, slot, data=None):
    #import pdb; pdb.set_trace()
    RtfvFormSet = formset_factory(ResourceTypeFacetValueForm, extra=0)
    init = []
    facets = pattern.facets_by_relationship(slot)
    for facet in facets:
        d = {"facet_id": facet.id,}
        init.append(d)
    formset = RtfvFormSet(initial=init, data=data)
    for form in formset:
        id = int(form["facet_id"].value())
        facet = Facet.objects.get(id=id)
        form.facet_name = facet.name
        fvs = pattern.facet_values_for_facet_and_relationship(facet, slot)
        fvs = list(set(fvs))
        choices = [(fv.id, fv.value) for fv in fvs]
        form.fields["value"].choices = choices
    return formset
    

