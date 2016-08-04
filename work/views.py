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
import json as simplejson
from django.utils.datastructures import SortedDict
from django.contrib.auth.forms import UserCreationForm
from django.conf import settings
from django.contrib.sites.models import Site

from valuenetwork.valueaccounting.models import *
from valuenetwork.valueaccounting.forms import *
from work.forms import *
from valuenetwork.valueaccounting.views import *
#from valuenetwork.valueaccounting.views import get_agent, get_help, get_site_name, resource_role_agent_formset, uncommit, commitment_finished, commit_to_task

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None
    
def get_site_name():
    return Site.objects.get_current().name

def work_home(request):

    return render_to_response("work_home.html", {
        "help": get_help("work_home"),
    }, 
        context_instance=RequestContext(request))

    
@login_required
def my_dashboard(request):
    #import pdb; pdb.set_trace()
    my_work = []
    my_skillz = []
    other_wip = []
    agent = get_agent(request)
    if agent:
        context_ids = [c.id for c in agent.related_contexts()]
        my_work = Commitment.objects.unfinished().filter(
            event_type__relationship="todo",
            from_agent=agent)
        skill_ids = agent.resource_types.values_list('resource_type__id', flat=True)
        my_skillz = Commitment.objects.unfinished().filter(
            from_agent=None, 
            context_agent__id__in=context_ids,
            event_type__relationship="todo",
            resource_type__id__in=skill_ids)
        other_unassigned = Commitment.objects.unfinished().filter(
            from_agent=None, 
            context_agent__id__in=context_ids,
            event_type__relationship="work").exclude(resource_type__id__in=skill_ids)  
        todos = Commitment.objects.unfinished().filter(
            from_agent=None, 
            context_agent__id__in=context_ids,
            event_type__relationship="todo")  
    else:
        other_unassigned = Commitment.objects.unfinished().filter(
            from_agent=None, 
            event_type__relationship="work")
    #import pdb; pdb.set_trace()
    my_todos = Commitment.objects.todos().filter(from_agent=agent)
    init = {"from_agent": agent,}
    patterns = PatternUseCase.objects.filter(use_case__identifier='todo')
    if patterns:
        pattern = patterns[0].pattern
        todo_form = WorkTodoForm(agent=agent, pattern=pattern, initial=init)
    else:
        todo_form = WorkTodoForm(agent=agent, initial=init)
    work_now = settings.USE_WORK_NOW
    return render_to_response("work/my_dashboard.html", {
        "agent": agent,
        "my_work": my_work,
        "my_skillz": my_skillz,
        "other_unassigned": other_unassigned,
        "my_todos": my_todos,
        "todo_form": todo_form,
        "work_now": work_now,
        "help": get_help("proc_log"),
    }, context_instance=RequestContext(request))
    
def map(request):
    agent = get_agent(request)
    locations = Location.objects.all()
    nolocs = Location.objects.filter(latitude=0.0)
    latitude = settings.MAP_LATITUDE
    longitude = settings.MAP_LONGITUDE
    zoom = settings.MAP_ZOOM
    return render_to_response("work/map.html", {
        "agent": agent,
        "locations": locations,
        "nolocs": nolocs,
        "latitude": latitude,
        "longitude": longitude,
        "zoom": zoom,
        "help": get_help("work_map"),
    }, context_instance=RequestContext(request))

@login_required
def profile(request):
    #import pdb; pdb.set_trace()
    agent = get_agent(request)
    change_form = AgentCreateForm(instance=agent)
    skills = EconomicResourceType.objects.filter(behavior="work")
    et_work = EventType.objects.get(name="Time Contribution")
    arts = agent.resource_types.filter(event_type=et_work)
    agent_skills = []
    for art in arts:
        agent_skills.append(art.resource_type)
    for skill in skills:
        skill.checked = False
        if skill in agent_skills:
            skill.checked = True
    upload_form = UploadAgentForm(instance=agent)
    has_associations = agent.all_has_associates()
    is_associated_with = agent.all_is_associates()
          
    return render_to_response("work/profile.html", {
        "agent": agent,
        "photo_size": (128, 128),
        "change_form": change_form,
        "upload_form": upload_form,
        "skills": skills,
        "has_associations": has_associations,
        "is_associated_with": is_associated_with,
        "help": get_help("profile"),
    }, context_instance=RequestContext(request))

@login_required
def change_personal_info(request, agent_id):
    agent = get_object_or_404(EconomicAgent, id=agent_id)
    user_agent = get_agent(request)
    if not user_agent:
        return render_to_response('valueaccounting/no_permission.html')
    change_form = AgentCreateForm(instance=agent, data=request.POST or None)
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        if change_form.is_valid():
            agent = change_form.save()
    return HttpResponseRedirect('/%s/'
        % ('work/profile'))

@login_required
def upload_picture(request, agent_id):
    agent = get_object_or_404(EconomicAgent, id=agent_id)
    user_agent = get_agent(request)
    if not user_agent:
        return render_to_response('valueaccounting/no_permission.html')
    form = UploadAgentForm(instance=agent, data=request.POST, files=request.FILES)
    if form.is_valid():
        data = form.cleaned_data
        agt = form.save(commit=False)                    
        agt.changed_by=request.user
        agt.save()
    
    return HttpResponseRedirect('/%s/'
        % ('work/profile'))

@login_required
def update_skills(request, agent_id):
    agent = get_object_or_404(EconomicAgent, id=agent_id)
    user_agent = get_agent(request)
    if not user_agent:
        return render_to_response('valueaccounting/no_permission.html')
    #import pdb; pdb.set_trace()
    et_work = EventType.objects.get(name="Time Contribution")
    arts = agent.resource_types.filter(event_type=et_work)
    old_skill_rts = []
    for art in arts:
        old_skill_rts.append(art.resource_type)
    new_skills_list = request.POST.getlist('skill')
    new_skill_rts = []
    for rt_id in new_skills_list:
        skill = EconomicResourceType.objects.get(id=int(rt_id))
        new_skill_rts.append(skill)
    for skill in old_skill_rts:
        if skill not in new_skill_rts:
            arts = AgentResourceType.objects.filter(agent=agent).filter(resource_type=skill)
            if arts:
                art = arts[0]
                art.delete()
    for skill in new_skill_rts:
        if skill not in old_skill_rts:
            art = AgentResourceType(
                agent=agent,
                resource_type=skill,
                event_type=et_work,
                created_by=request.user,
            )
            art.save()
    
    return HttpResponseRedirect('/%s/'
        % ('work/profile'))
        
@login_required
def add_worker_to_location(request, location_id, agent_id):
    if location_id and agent_id:
        location = get_object_or_404(Location, id=location_id)
        agent = get_object_or_404(EconomicAgent, id=agent_id)
        agent.primary_location = location
        agent.save()
        return HttpResponseRedirect('/%s/'
            % ('work/profile'))
    else:
        return HttpResponseRedirect('/%s/'
            % ('work/map'))

@login_required
def add_location_to_worker(request, agent_id):
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        agent = get_object_or_404(EconomicAgent, id=agent_id)
        data = request.POST
        address = data["address"]
        longitude = data["agentLongitude"]
        latitude = data["agentLatitude"]
        location, created = Location.objects.get_or_create(
            latitude=latitude,
            longitude=longitude,
            address=address)
        if created:
            location.name = address
            location.save()
        agent.primary_location = location
        agent.save()
        return HttpResponseRedirect('/%s/'
            % ('work/profile'))
    else:
        return HttpResponseRedirect('/%s/'
            % ('work/map'))
        
@login_required    
def process_logging(request, process_id):
    process = get_object_or_404(Process, id=process_id)
    pattern = process.process_pattern
    context_agent = process.context_agent
    #import pdb; pdb.set_trace()
    agent = get_agent(request)
    user = request.user
    logger = False
    worker = False
    super_logger = False
    todays_date = datetime.date.today()
    change_process_form = ProcessForm(instance=process)
    add_output_form = None
    add_citation_form = None
    add_consumable_form = None
    add_usable_form = None
    add_work_form = None
    unplanned_work_form = None
    unplanned_cite_form = None
    unplanned_consumption_form = None
    unplanned_use_form = None
    unplanned_output_form = None
    process_expense_form = None
    role_formset = None
    slots = []
    event_types = []
    work_now = settings.USE_WORK_NOW
    to_be_changed_requirement = None
    changeable_requirement = None
    
    work_reqs = process.work_requirements()
    consume_reqs = process.consumed_input_requirements()
    use_reqs = process.used_input_requirements()
    unplanned_work = process.uncommitted_work_events()
    
    if agent and pattern:
        slots = pattern.slots()
        event_types = pattern.event_types()
        #if request.user.is_superuser or request.user == process.created_by:
        if request.user.is_staff or request.user == process.created_by:
            logger = True
            super_logger = True
        #import pdb; pdb.set_trace()
        for req in work_reqs:
            req.changeform = req.change_work_form()
            if agent == req.from_agent:
                logger = True
                worker = True  
            init = {"from_agent": agent, 
                "event_date": todays_date,
                "is_contribution": True,}
            req.input_work_form_init = req.input_event_form_init(init=init)
        for req in consume_reqs:
            req.changeform = req.change_form()
        for req in use_reqs:
            req.changeform = req.change_form()
        for event in unplanned_work:
            event.changeform = UnplannedWorkEventForm(
                pattern=pattern,
                context_agent=context_agent,
                instance=event, 
                prefix=str(event.id))
        output_resource_types = pattern.output_resource_types()        
        unplanned_output_form = UnplannedOutputForm(prefix='unplannedoutput')
        unplanned_output_form.fields["resource_type"].queryset = output_resource_types
        role_formset = resource_role_agent_formset(prefix="resource")
        produce_et = EventType.objects.get(name="Resource Production")
        change_et = EventType.objects.get(name="Change")
        #import pdb; pdb.set_trace()
        if "out" in slots:
            if logger:
                if change_et in event_types:
                    to_be_changed_requirement = process.to_be_changed_requirements()
                    if to_be_changed_requirement:
                        to_be_changed_requirement = to_be_changed_requirement[0]
                    changeable_requirement = process.changeable_requirements()
                    if changeable_requirement:
                        changeable_requirement = changeable_requirement[0]
                else:
                    add_output_form = ProcessOutputForm(prefix='output')
                    add_output_form.fields["resource_type"].queryset = output_resource_types
        if "work" in slots:
            if agent:
                work_init = {
                    "from_agent": agent,
                    "is_contribution": True,
                } 
                work_resource_types = pattern.work_resource_types()
                if work_resource_types:
                    work_unit = work_resource_types[0].unit
                    #work_init = {"unit_of_quantity": work_unit,}
                    work_init = {
                        "from_agent": agent,
                        "unit_of_quantity": work_unit,
                        "is_contribution": True,
                    } 
                    unplanned_work_form = UnplannedWorkEventForm(prefix="unplanned", context_agent=context_agent, initial=work_init)
                    unplanned_work_form.fields["resource_type"].queryset = work_resource_types
                    #if logger:
                    #    add_work_form = WorkCommitmentForm(initial=work_init, prefix='work', pattern=pattern)
                else:
                    unplanned_work_form = UnplannedWorkEventForm(prefix="unplanned", pattern=pattern, context_agent=context_agent, initial=work_init)
                    #is this correct? see commented-out lines above
                if logger:
                    date_init = {"due_date": process.end_date,}
                    add_work_form = WorkCommitmentForm(prefix='work', pattern=pattern, initial=date_init)

        if "cite" in slots:
            unplanned_cite_form = UnplannedCiteEventForm(prefix='unplannedcite', pattern=pattern)
            if context_agent.unit_of_claim_value:
                cite_unit = context_agent.unit_of_claim_value
            if logger:
                add_citation_form = ProcessCitationForm(prefix='citation', pattern=pattern)   
        if "consume" in slots:
            unplanned_consumption_form = UnplannedInputEventForm(prefix='unplannedconsumption', pattern=pattern)
            if logger:
                add_consumable_form = ProcessConsumableForm(prefix='consumable', pattern=pattern)
        if "use" in slots:
            unplanned_use_form = UnplannedInputEventForm(prefix='unplannedusable', pattern=pattern)
            if logger:
                add_usable_form = ProcessUsableForm(prefix='usable', pattern=pattern)
        if "payexpense" in slots:
            process_expense_form = ProcessExpenseEventForm(prefix='processexpense', pattern=pattern)
    
    cited_ids = [c.resource.id for c in process.citations()]
    #import pdb; pdb.set_trace()
    citation_requirements = process.citation_requirements()
    for cr in citation_requirements:
        cr.resources = []
        for evt in cr.fulfilling_events():
            resource = evt.resource
            resource.event = evt
            cr.resources.append(resource)
    
    output_resource_ids = [e.resource.id for e in process.production_events() if e.resource]
    
    return render_to_response("work/process_logging.html", {
        "process": process,
        "change_process_form": change_process_form,
        "cited_ids": cited_ids,
        "citation_requirements": citation_requirements,
        "output_resource_ids": output_resource_ids,
        "agent": agent,
        "user": user,
        "logger": logger,
        "worker": worker,
        "super_logger": super_logger,
        "add_output_form": add_output_form,
        "add_citation_form": add_citation_form,
        "add_consumable_form": add_consumable_form,
        "add_usable_form": add_usable_form,
        "add_work_form": add_work_form,
        "unplanned_work_form": unplanned_work_form,
        "unplanned_cite_form": unplanned_cite_form,
        "unplanned_consumption_form": unplanned_consumption_form,
        "unplanned_use_form": unplanned_use_form,
        "unplanned_output_form": unplanned_output_form,
        "role_formset": role_formset,
        "process_expense_form": process_expense_form,
        "slots": slots,
        "to_be_changed_requirement": to_be_changed_requirement,
        "changeable_requirement": changeable_requirement,
        "work_reqs": work_reqs,        
        "consume_reqs": consume_reqs,
        "uncommitted_consumption": process.uncommitted_consumption_events(),
        "use_reqs": use_reqs,
        "uncommitted_use": process.uncommitted_use_events(),
        "uncommitted_process_expenses": process.uncommitted_process_expense_events(),
        "unplanned_work": unplanned_work,
        "work_now": work_now,
        "help": get_help("process_work"),
    }, context_instance=RequestContext(request))

@login_required
def non_process_logging(request):
    member = get_agent(request)
    if not member:
        return HttpResponseRedirect('/%s/'
            % ('work/work-home'))
        
    TimeFormSet = modelformset_factory(
        EconomicEvent,
        form=CasualTimeContributionForm,
        can_delete=False,
        extra=8,
        max_num=8,
        )
    init = []
    for i in range(0, 8):
        init.append({"is_contribution": True,})
    time_formset = TimeFormSet(
        queryset=EconomicEvent.objects.none(),
        initial = init,
        data=request.POST or None)
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        keep_going = request.POST.get("keep-going")
        just_save = request.POST.get("save")
        if time_formset.is_valid():
            events = time_formset.save(commit=False)
            pattern = None
            patterns = PatternUseCase.objects.filter(use_case__identifier='non_prod')
            if patterns:
                pattern = patterns[0].pattern
            else:
                raise ValidationError("no non-production ProcessPattern")
            if pattern:
                unit = Unit.objects.filter(
                    unit_type="time",
                    name__icontains="Hour")[0]
                for event in events:
                    if event.event_date and event.quantity:
                        event.from_agent=member
                        event.to_agent = event.context_agent.default_agent()
                        #event.is_contribution=True
                        rt = event.resource_type
                        event_type = pattern.event_type_for_resource_type("work", rt)
                        event.event_type=event_type
                        event.unit_of_quantity=unit
                        event.created_by=request.user
                        event.save()
            if keep_going:
                return HttpResponseRedirect('/%s/'
                    % ('work/non-process-logging'))
            else:
                return HttpResponseRedirect('/%s/'
                    % ('work/my-history'))
    
    return render_to_response("work/non_process_logging.html", {
        "member": member,
        "time_formset": time_formset,
        "help": get_help("non_proc_log"),
    }, context_instance=RequestContext(request))


@login_required
def my_history(request):
    #import pdb; pdb.set_trace()
    #agent = get_object_or_404(EconomicAgent, pk=agent_id)
    user_agent = get_agent(request)
    agent = user_agent
    user_is_agent = False
    if agent == user_agent:
        user_is_agent = True
    event_list = agent.contributions()
    no_bucket = 0
    with_bucket = 0
    event_value = Decimal("0.0")
    claim_value = Decimal("0.0")
    outstanding_claims = Decimal("0.0")
    claim_distributions = Decimal("0.0")
    claim_distro_events = []
    event_types = {e.event_type for e in event_list}
    filter_form = EventTypeFilterForm(event_types=event_types, data=request.POST or None)
    paid_filter = "U"
    if request.method == "POST":
        if filter_form.is_valid():
            #import pdb; pdb.set_trace()
            data = filter_form.cleaned_data
            et_ids = data["event_types"]
            start = data["start_date"]
            end = data["end_date"]
            paid_filter = data["paid_filter"]
            if start:
                event_list = event_list.filter(event_date__gte=start)
            if end:
                event_list = event_list.filter(event_date__lte=end)
            #belt and suspenders: if no et_ids, form is not valid
            if et_ids:
                event_list = event_list.filter(event_type__id__in=et_ids)

    for event in event_list:
        if event.bucket_rule_for_context_agent():
            with_bucket += 1
        else:
            no_bucket += 1
        for claim in event.claims():
            claim_value += claim.original_value
            outstanding_claims += claim.value
            for de in claim.distribution_events():
                claim_distributions += de.value
                claim_distro_events.append(de.event)
    et = EventType.objects.get(name="Distribution")
    all_distro_evts = EconomicEvent.objects.filter(to_agent=agent, event_type=et)
    other_distro_evts = [d for d in all_distro_evts if d not in claim_distro_events]
    other_distributions = sum(de.quantity for de in other_distro_evts)
    #took off csv export for now
    #event_ids = ",".join([str(event.id) for event in event_list]) 
                    
    if paid_filter == "U":
        event_list = list(event_list)
        for evnt in event_list:
            if evnt.owed_amount() == 0:
                    event_list.remove(evnt)
    
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
    
    #import pdb; pdb.set_trace()
    return render_to_response("work/my_history.html", {
        "agent": agent,
        "user_is_agent": user_is_agent,
        "events": events,
        "filter_form": filter_form,
        #"event_ids": event_ids,
        "no_bucket": no_bucket,
        "with_bucket": with_bucket,
        "claim_value": format(claim_value, ",.2f"),
        "outstanding_claims": format(outstanding_claims, ",.2f"),
        "claim_distributions": format(claim_distributions, ",.2f"),
        "other_distributions": format(other_distributions, ",.2f"),
        "help": get_help("my_history"),
    }, context_instance=RequestContext(request))

@login_required
def change_history_event(request, event_id):
    event = get_object_or_404(EconomicEvent, pk=event_id)
    page = request.GET.get("page")
    #import pdb; pdb.set_trace()
    event_form = event.change_form(data=request.POST or None)
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        page = request.POST.get("page")
        if event_form.is_valid():
            event = event_form.save(commit=False)
            event.changed_by = request.user
            event.save()
        agent = event.from_agent
        #next = request.POST.get("next")
        if page:
            #if next:
            #    if next == "work-contributions":
            #        return HttpResponseRedirect('/%s/'
            #            % ('work/my-history', page))
            return HttpResponseRedirect('/%s/'
                % ('work/my-history', page))
        else:
            #if next:
            #    if next == "work-contributions":
            #        return HttpResponseRedirect('/%s/'
            #            % ('work/my-history'))
            return HttpResponseRedirect('/%s/'
                % ('work/my-history'))
    return render_to_response("work/change_history_event.html", {
        "event_form": event_form,
        "page": page,
    }, context_instance=RequestContext(request)) 

'''
@login_required
def register_skills(request):
    #import pdb; pdb.set_trace()
    agent = get_agent(request)
    skills = EconomicResourceType.objects.filter(behavior="work")
    
    return render_to_response("work/register_skills.html", {
        "agent": agent,
        "skills": skills,
    }, context_instance=RequestContext(request))
'''

def create_worktimer_context(
        request, 
        process,
        agent,
        commitment):
    prev = ""
    today = datetime.date.today()
    #todo: will not now handle lack of commitment
    event = EconomicEvent(
        event_date=today,
        from_agent=agent,
        to_agent=process.default_agent(),
        process=process,
        context_agent=process.context_agent,
        quantity=Decimal("0"),
        is_contribution=True,
        created_by = request.user,
    )
        
    if commitment:
        event.commitment = commitment
        event.event_type = commitment.event_type
        event.resource_type = commitment.resource_type
        event.unit_of_quantity = commitment.resource_type.unit
        init = {
            "work_done": commitment.finished,
            "process_done": commitment.process.finished,
        }
        wb_form = WorkbookForm(initial=init)
        prev_events = commitment.fulfillment_events.filter(event_date__lt=today)
        if prev_events:
            prev_dur = sum(prev.quantity for prev in prev_events)
            unit = ""
            if commitment.unit_of_quantity:
                unit = commitment.unit_of_quantity.abbrev
            prev = " ".join([str(prev_dur), unit])
    else:
        wb_form = WorkbookForm()
    #if event.quantity > 0:
    event.save()    
    others_working = []
    other_work_reqs = []
    wrqs = process.work_requirements()
    if wrqs.count() > 1:
        for wrq in wrqs:
            if wrq.from_agent != commitment.from_agent:
                if wrq.from_agent:
                    wrq.has_labnotes = wrq.agent_has_labnotes(wrq.from_agent)
                    others_working.append(wrq)
                else:
                    other_work_reqs.append(wrq)
    return {
        "commitment": commitment,
        "process": process,
        "wb_form": wb_form,
        "others_working": others_working,
        "other_work_reqs": other_work_reqs,
        "today": today,
        "prev": prev,
        "event": event,
        "help": get_help("work_timer"),
    }

@login_required
def work_timer(
        request,
        process_id,
        commitment_id=None):
    process = get_object_or_404(Process, id=process_id)
    agent = get_agent(request) 
    ct = None  
    if commitment_id:
        ct = get_object_or_404(Commitment, id=commitment_id)    
        #if not request.user.is_superuser:
        #    if agent != ct.from_agent:
        #        return render_to_response('valueaccounting/no_permission.html')
    template_params = create_worktimer_context(
        request, 
        process,
        agent,
        ct, 
    )
    return render_to_response("work/work_timer.html",
        template_params,
        context_instance=RequestContext(request))

@login_required
def save_timed_work_now(request, event_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        event = get_object_or_404(EconomicEvent, id=event_id)      
        form = WorkbookForm(instance=event, data=request.POST)
        if form.is_valid():
            data = form.cleaned_data
            event = form.save(commit=False)
            event.changed_by = request.user
            process = event.process
            event.save()
            if not process.started:
                process.started = event.event_date
                process.changed_by=request.user
                process.save()            
            data = "ok"
        else:
            data = form.errors
        return HttpResponse(data, content_type="text/plain")

@login_required
def work_process_finished(request, process_id):
    #import pdb; pdb.set_trace()
    process = get_object_or_404(Process, pk=process_id)
    if not process.finished:
        process.finished = True
        process.save()
    else:
        if process.finished:
            process.finished = False
            process.save()
    return HttpResponseRedirect('/%s/%s/'
        % ('work/process-logging', process_id))

@login_required
def manage_faircoin_account(request, resource_id):
    #import pdb; pdb.set_trace()
    resource = get_object_or_404(EconomicResource, id=resource_id)
    agent = get_agent(request)
    send_coins_form = None
    limit = 0
    if agent:
        if agent.owns(resource):
            send_coins_form = SendFairCoinsForm()
            from valuenetwork.valueaccounting.faircoin_utils import network_fee
            limit = resource.spending_limit()
    return render_to_response("work/faircoin_account.html", {
        "resource": resource,
        "photo_size": (128, 128),
        "agent": agent,
        "send_coins_form": send_coins_form,
        "limit": limit,
    }, context_instance=RequestContext(request))
    
@login_required
def change_faircoin_account(request, resource_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        resource = get_object_or_404(EconomicResource, pk=resource_id)
        form = EconomicResourceForm(data=request.POST, instance=resource)
        if form.is_valid():
            data = form.cleaned_data
            resource = form.save(commit=False)
            resource.changed_by=request.user
            resource.save()
            """
            RraFormSet = modelformset_factory(
                AgentResourceRole,
                form=ResourceRoleAgentForm,
                can_delete=True,
                extra=4,
                )
            role_formset = RraFormSet(
                prefix="role", 
                queryset=resource.agent_resource_roles.all(),
                data=request.POST
                )
            if role_formset.is_valid():
                saved_formset = role_formset.save(commit=False)
                for role in saved_formset:
                    role.resource = resource
                    role.save()
            """
            return HttpResponseRedirect('/%s/%s/'
                % ('work/manage-faircoin-account', resource_id))
        else:
            raise ValidationError(form.errors)

@login_required
def transfer_faircoins(request, resource_id):
    if request.method == "POST":
        resource = get_object_or_404(EconomicResource, id=resource_id)
        agent = get_agent(request)
        send_coins_form = SendFairCoinsForm(data=request.POST)
        if send_coins_form.is_valid():
            data = send_coins_form.cleaned_data
            address_end = data["to_address"]
            quantity = data["quantity"]
            address_origin = resource.digital_currency_address
            if address_origin and address_end:
                from_agent = resource.owner()
                to_resources = EconomicResource.objects.filter(digital_currency_address=address_end)
                to_agent = None
                if to_resources:
                    to_resource = to_resources[0] #shd be only one
                    to_agent = to_resource.owner()
                et_give = EventType.objects.get(name="Give")
                if to_agent:
                    tt = faircoin_internal_transfer_type()
                    xt = tt.exchange_type
                    date = datetime.date.today()
                    exchange = Exchange(
                        exchange_type=xt,
                        use_case=xt.use_case,
                        name="Transfer Faircoins",
                        start_date=date,
                        )
                    exchange.save()
                    transfer = Transfer(
                        transfer_type=tt,
                        exchange=exchange,
                        transfer_date=date,
                        name="Transfer Faircoins",
                        )
                    transfer.save()
                else:
                    tt = faircoin_outgoing_transfer_type()
                    xt = tt.exchange_type
                    date = datetime.date.today()
                    exchange = Exchange(
                        exchange_type=xt,
                        use_case=xt.use_case,
                        name="Send Faircoins",
                        start_date=date,
                        )
                    exchange.save()
                    transfer = Transfer(
                        transfer_type=tt,
                        exchange=exchange,
                        transfer_date=date,
                        name="Send Faircoins",
                        )
                    transfer.save()
                    
                # network_fee is subtracted from quantity
                # so quantity is correct for the giving event 
                # but receiving event will get quantity - network_fee
                state =  "new"
                event = EconomicEvent(
                    event_type = et_give,
                    event_date = date,
                    from_agent=from_agent,
                    to_agent=to_agent,
                    resource_type=resource.resource_type,
                    resource=resource,
                    digital_currency_tx_state = state,
                    quantity = quantity, 
                    transfer=transfer,
                    event_reference=address_end,
                    )
                event.save()
                if to_agent:
                    from valuenetwork.valueaccounting.faircoin_utils import network_fee
                    quantity = quantity - Decimal(float(network_fee()) / 1.e6)
                    et_receive = EventType.objects.get(name="Receive")
                    event = EconomicEvent(
                        event_type = et_receive,
                        event_date = date,
                        from_agent=from_agent,
                        to_agent=to_agent,
                        resource_type=to_resource.resource_type,
                        resource=to_resource,
                        digital_currency_tx_state = state,
                        quantity = quantity, 
                        transfer=transfer,
                        event_reference=address_end,
                        )
                    event.save()
                    print "receive event:", event
                        
                return HttpResponseRedirect('/%s/%s/'
                    % ('work/faircoin-history', resource.id))

        return HttpResponseRedirect('/%s/%s/'
                % ('work/manage-faircoin-account', resource.id))
                    
@login_required
def transfer_faircoins_old(request, resource_id):
    if request.method == "POST":
        resource = get_object_or_404(EconomicResource, id=resource_id)
        agent = get_agent(request)
        send_coins_form = SendFairCoinsForm(data=request.POST)
        if send_coins_form.is_valid():
            data = send_coins_form.cleaned_data
            address_end = data["to_address"]
            quantity = data["quantity"]
            address_origin = resource.digital_currency_address
            if address_origin and address_end:
                from valuenetwork.valueaccounting.faircoin_utils import send_faircoins, get_confirmations, network_fee
                tx, broadcasted = send_faircoins(address_origin, address_end, quantity)
                if tx:
                    tx_hash = tx.hash()
                    from_agent = resource.owner()
                    to_resources = EconomicResource.objects.filter(digital_currency_address=address_end)
                    to_agent = None
                    if to_resources:
                        to_resource = to_resources[0] #shd be only one
                        to_agent = to_resource.owner()
                    et_give = EventType.objects.get(name="Give")
                    if to_agent:
                        tt = faircoin_internal_transfer_type()
                        xt = tt.exchange_type
                        date = datetime.date.today()
                        exchange = Exchange(
                            exchange_type=xt,
                            use_case=xt.use_case,
                            name="Transfer Faircoins",
                            start_date=date,
                            )
                        exchange.save()
                        transfer = Transfer(
                            transfer_type=tt,
                            exchange=exchange,
                            transfer_date=date,
                            name="Transfer Faircoins",
                            )
                        transfer.save()
                    else:
                        tt = faircoin_outgoing_transfer_type()
                        xt = tt.exchange_type
                        date = datetime.date.today()
                        exchange = Exchange(
                            exchange_type=xt,
                            use_case=xt.use_case,
                            name="Send Faircoins",
                            start_date=date,
                            )
                        exchange.save()
                        transfer = Transfer(
                            transfer_type=tt,
                            exchange=exchange,
                            transfer_date=date,
                            name="Send Faircoins",
                            )
                        transfer.save()
                     
                    # network_fee is subtracted from quantity
                    # so quantity is correct for the giving event 
                    # but receiving event will get quantity - network_fee
                    state = "pending"
                    if not broadcasted:
                        confirmations = get_confirmations(tx_hash)
                        if confirmations[0]:
                            print "got broadcasted in view"
                            broadcasted = True
                    if broadcasted:
                        state = "broadcast"
                    event = EconomicEvent(
                        event_type = et_give,
                        event_date = date,
                        from_agent=from_agent,
                        to_agent=to_agent,
                        resource_type=resource.resource_type,
                        resource=resource,
                        digital_currency_tx_hash = tx_hash,
                        digital_currency_tx_state = state,
                        quantity = quantity, 
                        transfer=transfer,
                        event_reference=address_end,
                        )
                    event.save()
                    if to_agent:
                        outputs = tx.get_outputs()
                        value = 0
                        for address, val in outputs:
                            if address == address_end:
                                value = val
                        if value:
                            quantity = Decimal(value / 1.e6)
                        else:
                            quantity = quantity - Decimal(float(network_fee) / 1.e6)
                        et_receive = EventType.objects.get(name="Receive")
                        event = EconomicEvent(
                            event_type = et_receive,
                            event_date = date,
                            from_agent=from_agent,
                            to_agent=to_agent,
                            resource_type=to_resource.resource_type,
                            resource=to_resource,
                            digital_currency_tx_hash = tx_hash,
                            digital_currency_tx_state = state,
                            quantity = quantity, 
                            transfer=transfer,
                            )
                        event.save()
                        print "receive event:", event
                        
                    return HttpResponseRedirect('/%s/%s/'
                        % ('work/faircoin-history', resource.id))

            return HttpResponseRedirect('/%s/%s/'
                    % ('work/manage-faircoin-account', resource.id))

def faircoin_history(request, resource_id):
    resource = get_object_or_404(EconomicResource, id=resource_id)
    event_list = resource.events.all()
    agent = get_agent(request)
    init = {"quantity": resource.quantity,}
    unit = resource.resource_type.unit
    
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
    
    return render_to_response("work/faircoin_history.html", {
        "resource": resource,
        "agent": agent,
        "unit": unit,
        "events": events,
    }, context_instance=RequestContext(request))
    
def membership_request(request):
    membership_form = MembershipRequestForm(data=request.POST or None)
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        if membership_form.is_valid():
            data = membership_form.cleaned_data
            name = data["name"]
            surname = data["surname"]
            type_of_membership = data["type_of_membership"]
            description = data["description"]
            membership_form.save()
            if notification:
                #import pdb; pdb.set_trace()
                users = User.objects.filter(is_staff=True)
                if users:
                    site_name = get_site_name()
                    notification.send(
                        users, 
                        "work_membership_request", 
                        {"name": name,
                        "surname": surname,
                        "type_of_membership": type_of_membership,
                        "description": description,
                        "site_name": site_name,
                        }
                    )
            return HttpResponseRedirect('/%s/'
                % ('work/membershipthanks'))
    return render_to_response("work/membership_request.html", {
        "help": get_help("work_membership_request"),
        "membership_form": membership_form,
    }, context_instance=RequestContext(request))

@login_required
def add_todo(request):
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        patterns = PatternUseCase.objects.filter(use_case__identifier='todo')
        if patterns:
            pattern = patterns[0].pattern
            form = TodoForm(data=request.POST, pattern=pattern)
        else:
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
                todo.quantity = Decimal("0")
                todo.unit_of_quantity=todo.resource_type.unit
                todo.save()
                if notification:
                    if todo.from_agent:
                        if todo.from_agent != agent:
                            site_name = get_site_name()
                            user = todo.from_agent.user()
                            if user:
                                #import pdb; pdb.set_trace()
                                notification.send(
                                    [user.user,], 
                                    "valnet_new_todo", 
                                    {"description": todo.description,
                                    "creator": agent,
                                    "site_name": site_name,
                                    }
                                )
            
    return HttpResponseRedirect(next)

