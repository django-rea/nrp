import datetime

from django.db.models import Q
from django.http import HttpResponse, HttpResponseServerError, Http404, HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib import messages
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
from django.core import validators
from django.utils.translation import ugettext, ugettext_lazy as _

from valuenetwork.valueaccounting.models import *
from valuenetwork.valueaccounting.forms import *
from work.forms import *
from valuenetwork.valueaccounting.views import *
#from valuenetwork.valueaccounting.views import get_agent, get_help, get_site_name, resource_role_agent_formset, uncommit, commitment_finished, commit_to_task

from fobi.models import FormEntry

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None

def get_site_name():
    return Site.objects.get_current().name

def get_url_starter():
    return "".join(["https://", Site.objects.get_current().domain])

def work_home(request):

    return render_to_response("work_home.html", {
        "help": get_help("work_home"),
    },
        context_instance=RequestContext(request))


@login_required
def my_dashboard(request):
    #import pdb; pdb.set_trace()
    agent = get_agent(request)

    return render_to_response("work/my_dashboard.html", {
        "agent": agent,
    }, context_instance=RequestContext(request))


@login_required
def my_tasks(request):
    #import pdb; pdb.set_trace()
    my_work = []
    #my_skillz = []
    other_wip = []
    agent = get_agent(request)
    #if agent:
    context_ids = [c.id for c in agent.related_contexts()]
    my_work = Commitment.objects.unfinished().filter(
        event_type__relationship="work",
        from_agent=agent)
    #skill_ids = agent.resource_types.values_list('resource_type__id', flat=True)
    #my_skillz = Commitment.objects.unfinished().filter(
    #    from_agent=None,
    #    context_agent__id__in=context_ids,
    #    event_type__relationship="todo",
    #    resource_type__id__in=skill_ids)
    #other_unassigned = Commitment.objects.unfinished().filter(
    #    from_agent=None,
    #    context_agent__id__in=context_ids,
    #    event_type__relationship="work").exclude(resource_type__id__in=skill_ids)
    todos = Commitment.objects.unfinished().filter(
        from_agent=None,
        context_agent__id__in=context_ids,
        event_type__relationship="todo")
    #else:
    #    other_unassigned = Commitment.objects.unfinished().filter(
    #        from_agent=None,
    #        event_type__relationship="work")
    #import pdb; pdb.set_trace()
    my_todos = Commitment.objects.todos().filter(from_agent=agent)
    init = {"from_agent": agent,}
    patterns = PatternUseCase.objects.filter(use_case__identifier='todo')
    if patterns:
        pattern = patterns[0].pattern
        todo_form = WorkTodoForm(agent=agent, pattern=pattern, initial=init)
    else:
        todo_form = WorkTodoForm(agent=agent, initial=init)
    #work_now = settings.USE_WORK_NOW
    return render_to_response("work/my_tasks.html", {
        "agent": agent,
        "my_work": my_work,
        #"my_skillz": my_skillz,
        #"other_unassigned": other_unassigned,
        "my_todos": my_todos,
        "todo_form": todo_form,
        #"work_now": work_now,
        "help": get_help("proc_log"),
    }, context_instance=RequestContext(request))

@login_required
def take_new_tasks(request):
    #import pdb; pdb.set_trace()
    #my_work = []
    my_skillz = []
    other_wip = []
    agent = get_agent(request)
    #if agent:
    context_ids = [c.id for c in agent.related_contexts()]
    #my_work = Commitment.objects.unfinished().filter(
    #    event_type__relationship="todo",
    #    from_agent=agent)
    skill_ids = agent.resource_types.values_list('resource_type__id', flat=True)
    my_skillz = Commitment.objects.unfinished().filter(
        from_agent=None,
        context_agent__id__in=context_ids,
        event_type__relationship="work",
        resource_type__id__in=skill_ids)
    #other_unassigned = Commitment.objects.unfinished().filter(
    #    from_agent=None,
    #    context_agent__id__in=context_ids,
    #    event_type__relationship="work").exclude(resource_type__id__in=skill_ids)
    todos = Commitment.objects.unfinished().filter(
        from_agent=None,
        context_agent__id__in=context_ids,
        event_type__relationship="todo")
    #else:
    #    other_unassigned = Commitment.objects.unfinished().filter(
    #        from_agent=None,
    #        event_type__relationship="work")
    #import pdb; pdb.set_trace()
    my_todos = Commitment.objects.todos().filter(from_agent=agent)
    init = {"from_agent": agent,}
    patterns = PatternUseCase.objects.filter(use_case__identifier='todo')
    if patterns:
        pattern = patterns[0].pattern
        todo_form = WorkTodoForm(agent=agent, pattern=pattern, initial=init)
    else:
        todo_form = WorkTodoForm(agent=agent, initial=init)
    #work_now = settings.USE_WORK_NOW
    return render_to_response("work/take_new_tasks.html", {
        "agent": agent,
        #"my_work": my_work,
        "my_skillz": my_skillz,
        #"other_unassigned": other_unassigned,
        #"my_todos": my_todos,
        #"todo_form": todo_form,
        #"work_now": work_now,
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
    change_form = WorkAgentCreateForm(instance=agent)
    skills = EconomicResourceType.objects.filter(behavior="work")
    et_work = EventType.objects.get(name="Time Contribution")
    arts = agent.resource_types.filter(event_type=et_work)
    agent_skills = []
    user = request.user
    suggestions = user.skill_suggestion.all()
    suggested_skills = [sug.resource_type for sug in suggestions]
    for art in arts:
        agent_skills.append(art.resource_type)
    for skill in skills:
        skill.checked = False
        if skill in agent_skills:
            skill.checked = True
        if skill in suggested_skills:
            skill.thanks = True
    upload_form = UploadAgentForm(instance=agent)
    has_associations = agent.all_has_associates()
    is_associated_with = agent.all_is_associates()
    other_form = SkillSuggestionForm()
    suggestions = request.user.skill_suggestion.all()
    faircoin_account = agent.faircoin_resource()
    balance = 0
    if faircoin_account:
        balance = faircoin_account.digital_currency_balance()

    other_form = SkillSuggestionForm()
    suggestions = request.user.skill_suggestion.all()
    #balance = 2
    candidate_membership = agent.candidate_membership()

    return render_to_response("work/profile.html", {
        "agent": agent,
        "photo_size": (128, 128),
        "change_form": change_form,
        "upload_form": upload_form,
        "skills": skills,
        "has_associations": has_associations,
        "is_associated_with": is_associated_with,
        "faircoin_account": faircoin_account,
        "balance": balance,
        #"payment_due": payment_due,
        "candidate_membership": candidate_membership,
        "other_form": other_form,
        "suggestions": suggestions,
        "help": get_help("profile"),
        #"share_price": share_price,
        #"number_of_shares": number_of_shares,
        #"can_pay": can_pay,
    }, context_instance=RequestContext(request))

@login_required
def share_payment(request, agent_id):
    #import pdb; pdb.set_trace()
    agent = get_object_or_404(EconomicAgent, id=agent_id)
    agent_account = agent.faircoin_resource()
    balance = agent_account.digital_currency_balance()
    #balance = 2
    candidate_membership = agent.candidate_membership()
    share = EconomicResourceType.objects.membership_share()
    share_price = share.price_per_unit
    number_of_shares = agent.number_of_shares()
    share_price = share_price * number_of_shares

    if share_price <= balance:
        pay_to_id = settings.SEND_MEMBERSHIP_PAYMENT_TO
        pay_to_agent = EconomicAgent.objects.get(nick=pay_to_id)
        pay_to_account = pay_to_agent.faircoin_resource()
        quantity = Decimal(share_price)
        address_origin = agent_account.digital_currency_address
        address_end = pay_to_account.digital_currency_address
        xt = ExchangeType.objects.membership_share_exchange_type()
        tts = xt.transfer_types.all()
        tt_share = tts.get(name__contains="Share")
        tt_fee = tts.get(name__contains="Fee")
        from_agent = agent
        to_resource = pay_to_account
        to_agent = pay_to_agent
        et_give = EventType.objects.get(name="Give")
        et_receive = EventType.objects.get(name="Receive")
        date = datetime.date.today()
        fc = EconomicAgent.objects.freedom_coop()

        exchange = Exchange(
            exchange_type=xt,
            use_case=xt.use_case,
            name="Transfer Faircoins",
            start_date=date,
            )
        exchange.save()

        transfer_fee = Transfer(
            transfer_type=tt_fee,
            exchange=exchange,
            transfer_date=date,
            name="Transfer Faircoins",
            )
        transfer_fee.save()

        transfer_membership = Transfer(
            transfer_type=tt_share,
            exchange=exchange,
            transfer_date=date,
            name="Transfer Membership",
            )
        transfer_membership.save()

        # network_fee is subtracted from quantity
        # so quantity is correct for the giving event
        # but receiving event will get quantity - network_fee
        state =  "new"
        resource = agent_account
        event = EconomicEvent(
            event_type = et_give,
            event_date = date,
            from_agent=from_agent,
            to_agent=to_agent,
            resource_type=resource.resource_type,
            resource=resource,
            digital_currency_tx_state = state,
            quantity = quantity,
            transfer=transfer_fee,
            event_reference=address_end,
            )
        event.save()

        from valuenetwork.valueaccounting.faircoin_utils import network_fee
        quantity = quantity - Decimal(float(network_fee()) / 1.e6)

        event = EconomicEvent(
            event_type = et_receive,
            event_date = date,
            from_agent=from_agent,
            to_agent=to_agent,
            resource_type=to_resource.resource_type,
            resource=to_resource,
            digital_currency_tx_state = state,
            quantity = quantity,
            transfer=transfer_fee,
            event_reference=address_end,
            )
        event.save()

        #import pdb; pdb.set_trace()
        quantity = Decimal(number_of_shares)
        resource = EconomicResource(
            resource_type=share,
            quantity=quantity,
            identifier=" ".join([from_agent.name, share.name]),
            )
        resource.save()

        owner_role = AgentResourceRoleType.objects.owner_role()

        arr = AgentResourceRole(
            agent=from_agent,
            resource=resource,
            role=owner_role,
            is_contact=True,
            )
        arr.save()

        event = EconomicEvent(
            event_type = et_give,
            event_date = date,
            from_agent=to_agent,
            to_agent=from_agent,
            resource_type=resource.resource_type,
            resource=resource,
            quantity = quantity,
            transfer=transfer_membership,
            )
        event.save()

        event = EconomicEvent(
            event_type = et_receive,
            event_date = date,
            from_agent=to_agent,
            to_agent=from_agent,
            resource_type=resource.resource_type,
            resource=resource,
            quantity = quantity,
            transfer=transfer_membership,
            )
        event.save()

        #import pdb; pdb.set_trace()
        aa = agent.candidate_association()

        if aa:
            if aa.has_associate == pay_to_agent:
                aa.delete()

        association_type = AgentAssociationType.objects.get(name="Member")
        fc_aa = AgentAssociation(
            is_associate=agent,
            has_associate=fc,
            association_type=association_type,
            state="active",
            )
        fc_aa.save()

    return HttpResponseRedirect('/%s/'
        % ('work/home'))

@login_required
def project_work(request):
    #import pdb; pdb.set_trace()
    agent = get_agent(request)
    projects = agent.related_contexts()
    if not agent or agent.is_participant_candidate():
        return render_to_response('work/no_permission.html')
    next = "/work/project-work/"
    context_id = 0
    start = datetime.date.today() - datetime.timedelta(days=30)
    end = datetime.date.today() + datetime.timedelta(days=90)
    init = {"start_date": start, "end_date": end}
    date_form = DateSelectionForm(initial=init, data=request.POST or None)
    ca_form = WorkProjectSelectionFormOptional(data=request.POST or None, context_agents=projects)
    chosen_context_agent = None
    patterns = PatternUseCase.objects.filter(use_case__identifier='todo')
    if patterns:
        pattern = patterns[0].pattern
        todo_form = WorkTodoForm(pattern=pattern, agent=agent)
    else:
        todo_form = WorkTodoForm(agent=agent)
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        if date_form.is_valid():
            dates = date_form.cleaned_data
            start = dates["start_date"]
            end = dates["end_date"]
            if ca_form.is_valid():
                proj_data = ca_form.cleaned_data
                proj_id = proj_data["context_agent"]
                if proj_id.isdigit:
                    context_id = proj_id
                    chosen_context_agent = EconomicAgent.objects.get(id=proj_id)

    start_date = start.strftime('%Y_%m_%d')
    end_date = end.strftime('%Y_%m_%d')
    #processes, context_agents = assemble_schedule(start, end, chosen_context_agent)
    #my_context_agents = []
    #for ca in context_agents:
    #    if ca in projects:
    #        my_context_agents.append(ca)
    todos = Commitment.objects.todos().filter(due_date__range=(start, end))
    if chosen_context_agent:
        todos = todos.filter(context_agent=chosen_context_agent)
    my_project_todos = []
    for todo in todos:
        if todo.context_agent in projects:
            my_project_todos.append(todo)
    return render_to_response("work/project_work.html", {
        "agent": agent,
        #"context_agents": my_context_agents,
        "all_processes": projects,
        "date_form": date_form,
        "start_date": start_date,
        "end_date": end_date,
        "context_id": context_id,
        "todo_form": todo_form,
        "ca_form": ca_form,
        "todos": my_project_todos,
        "next": next,
        "help": get_help("project_work"),
    }, context_instance=RequestContext(request))


@login_required
def change_personal_info(request, agent_id):
    agent = get_object_or_404(EconomicAgent, id=agent_id)
    user_agent = get_agent(request)
    if not user_agent:
        return render_to_response('work/no_permission.html')
    change_form = WorkAgentCreateForm(instance=agent, data=request.POST or None)
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
    if request.method == "POST":
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
        new_skills_list = request.POST.getlist('skillChoice')
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
        other_form = SkillSuggestionForm(data=request.POST)
        #import pdb; pdb.set_trace()
        if other_form.is_valid():
            suggestion = other_form.save(commit=False)
            suggestion.suggested_by = request.user
            suggestion.save()
            try:
                suggester = request.user.agent.agent
            except:
                suggester = request.user
            if notification:
                users = User.objects.filter(is_staff=True)
                suggestions_url = get_url_starter() + "/accounting/skill-suggestions/"
                if users:
                    site_name = get_site_name()
                    notification.send(
                        users,
                        "work_skill_suggestion",
                        {"skill": suggestion.skill,
                        "suggested_by": suggester.name,
                        "suggestions_url": suggestions_url,
                        }
                    )

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
        form=WorkCasualTimeContributionForm,
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

    payment_due = False
    candidate_membership = None
    share_price = False
    number_of_shares = False
    can_pay = False
    faircoin_account = False
    balance = False

    if agent:
        if agent.owns(resource):
            send_coins_form = SendFairCoinsForm()
            #from valuenetwork.valueaccounting.faircoin_utils import network_fee
            limit = resource.spending_limit()

        candidate_membership = agent.candidate_membership()
        if candidate_membership:
            faircoin_account = agent.faircoin_resource()
            balance = 0
            if faircoin_account:
                balance = faircoin_account.digital_currency_balance()
            share = EconomicResourceType.objects.membership_share()
            share_price = share.price_per_unit
            number_of_shares = agent.number_of_shares()
            share_price = share_price * number_of_shares
            payment_due = False
            if not agent.owns_resource_of_type(share):
                payment_due = True
            can_pay = balance >= share_price

    return render_to_response("work/faircoin_account.html", {
        "resource": resource,
        "photo_size": (128, 128),
        "agent": agent,
        "send_coins_form": send_coins_form,
        "limit": limit,

        "payment_due": payment_due,
        "candidate_membership": candidate_membership,
        "help": get_help("profile"),
        "share_price": share_price,
        "number_of_shares": number_of_shares,
        "can_pay": can_pay,
        "faircoin_account": faircoin_account,
        "balance": balance,

    }, context_instance=RequestContext(request))

def validate_faircoin_address_for_worker(request):
    #import pdb; pdb.set_trace()
    from valuenetwork.valueaccounting.faircoin_utils import is_valid
    data = request.GET
    address = data["to_address"]
    answer = is_valid(address)
    if not answer:
        answer = "Invalid FairCoin address"
    response = simplejson.dumps(answer, ensure_ascii=False)
    return HttpResponse(response, content_type="text/json-comment-filtered")

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
        #import pdb; pdb.set_trace()
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
                    #print "receive event:", event

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
            human = True
            data = membership_form.cleaned_data
            type_of_membership = data["type_of_membership"]
            number_of_shares = data["number_of_shares"]
            name = data["name"]
            surname = data["surname"]
            description = data["description"]
            mbr_req = membership_form.save()

            event_type = EventType.objects.get(relationship="todo")
            description = "Create an Agent and User for the Membership Request from "
            description += name
            membership_url= get_url_starter() + "/accounting/membership-request/" + str(mbr_req.id) + "/"
            context_agent=EconomicAgent.objects.get(name__icontains="Membership Request")
            resource_types = EconomicResourceType.objects.filter(behavior="work")
            rts = resource_types.filter(
                Q(name__icontains="Admin")|
                Q(name__icontains="Coop")|
                Q(name__icontains="Work"))
            if rts:
                rt = rts[0]
            else:
                rt = resource_types[0]

            task = Commitment(
                event_type=event_type,
                description=description,
                resource_type=rt,
                context_agent=context_agent,
                url=membership_url,
                due_date=datetime.date.today(),
                quantity=Decimal("1")
                )
            task.save()


            if notification:
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
                        "membership_url": membership_url,
                        }
                    )

            return HttpResponseRedirect('/%s/'
                % ('membershipthanks'))
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

def membership_discussion(request, membership_request_id):
    user_agent = get_agent(request)
    mbr_req = get_object_or_404(MembershipRequest, pk=membership_request_id)
    allowed = False
    if user_agent:
        if user_agent.membership_request() == mbr_req or request.user.is_staff:
            allowed = True
    if not allowed:
        return render_to_response('valueaccounting/no_permission.html')

    return render_to_response("work/membership_request_with_comments.html", {
        "help": get_help("membership_request"),
        "mbr_req": mbr_req,
        "user_agent": user_agent,
    }, context_instance=RequestContext(request))

@login_required
def work_todo_done(request, todo_id):
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

@login_required
def work_add_todo(request):
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

@login_required
def work_todo_delete(request, todo_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        try:
            todo = Commitment.objects.get(id=todo_id)
        except Commitment.DoesNotExist:
            todo = None
        if todo:
            if notification:
                if todo.from_agent:
                    agent = get_agent(request)
                    if todo.from_agent != agent:
                        site_name = get_site_name()
                        user = todo.from_agent.user()
                        if user:
                            #import pdb; pdb.set_trace()
                            notification.send(
                                [user.user,],
                                "valnet_deleted_todo",
                                {"description": todo.description,
                                "creator": agent,
                                "site_name": site_name,
                                }
                            )
            todo.delete()
    next = request.POST.get("next")
    return HttpResponseRedirect(next)

@login_required
def work_todo_change(request, todo_id):
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

@login_required
def work_todo_decline(request, todo_id):
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

@login_required
def work_todo_time(request):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        todo_id = request.POST.get("todoId")
        try:
            todo = Commitment.objects.get(id=todo_id)
        except Commitment.DoesNotExist:
            todo = None
        if todo:
            hours = request.POST.get("hours")
            if hours:
                qty = Decimal(hours)
            else:
                qty = Decimal("0.0")
            event = todo.todo_event()
            if event:
                event.quantity = qty
                event.save()
            else:
                event = create_event_from_todo(todo)
                event.quantity = qty
                event.save()
    return HttpResponse("Ok", content_type="text/plain")

@login_required
def work_todo_mine(request, todo_id):
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
    next = request.POST.get("next")
    if next:
        return HttpResponseRedirect(next)
    return HttpResponseRedirect('/%s/'
        % ('work/my-dashboard'))

@login_required
def work_todo_description(request):
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
    return HttpResponse("Ok", content_type="text/plain")

@login_required
def work_commit_to_task(request, commitment_id):
    if request.method == "POST":
        ct = get_object_or_404(Commitment, id=commitment_id)
        process = ct.process
        agent = get_agent(request)
        prefix = ct.form_prefix()
        form = CommitmentForm(data=request.POST, prefix=prefix)
        next = None
        next = request.POST.get("next")
        #import pdb; pdb.set_trace()
        if form.is_valid():
            data = form.cleaned_data
            #todo: next line did not work, don't want to take time to figure out why right now
            #probly form shd have ct as instance.
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
            ct.changed_by=request.user
            ct.save()
    if next:
        return HttpResponseRedirect(next)
    return HttpResponseRedirect('/%s/'
        % ('work/my-dashboard'))

@login_required
def work_delete_event(request, event_id):
    #import pdb; pdb.set_trace()
    if request.method == "POST":
        event = get_object_or_404(EconomicEvent, pk=event_id)
        agent = event.from_agent
        process = event.process
        exchange = event.exchange
        distribution = event.distribution
        resource = event.resource
        if resource:
            if event.consumes_resources():
                resource.quantity += event.quantity
            if event.creates_resources():
                resource.quantity -= event.quantity
            if event.changes_stage():
                tbcs = process.to_be_changed_requirements()
                if tbcs:
                    tbc = tbcs[0]
                    tbc_evts = tbc.fulfilling_events()
                    if tbc_evts:
                        tbc_evt = tbc_evts[0]
                        resource.quantity = tbc_evt.quantity
                        tbc_evt.delete()
                    resource.stage = tbc.stage
                else:
                    resource.revert_to_previous_stage()
            event.delete()
            if resource.is_deletable():
                resource.delete()
            else:
                resource.save()
        else:
            event.delete()

    next = request.POST.get("next")
    if next:
        return HttpResponseRedirect(next)
    return HttpResponseRedirect('/%s/'
        % ('work/my-history'))

# bum2
@login_required
def your_projects(request):
    #import pdb; pdb.set_trace()
    agent = get_agent(request)
    agent_form = ProjectCreateForm() #initial={'agent_type': 'Project'})
    projects = agent.related_contexts()
    managed_projects = agent.managed_projects()
    join_projects = Project.objects.all() #filter(joining_style="moderated", visibility!="private")
    next = "/work/your-projects/"
    allowed = False
    if agent:
        if agent.is_active_freedom_coop_member() or request.user.is_staff or agent.is_participant():
            allowed = True
    if not allowed:
        return render_to_response('work/no_permission.html')

    roots = [p for p in projects if not p.is_root()] # if p.is_root()

    for root in roots:
        root.nodes = root.child_tree()
        annotate_tree_properties(root.nodes)
        #import pdb; pdb.set_trace()
        for node in root.nodes:
            aats = []
            for aat in node.agent_association_types():
                #if aat.association_behavior != "child":
                    aat.assoc_count = node.associate_count_of_type(aat.identifier)
                    assoc_list = node.all_has_associates_by_type(aat.identifier)
                    for assoc in assoc_list:
                        association = AgentAssociation.objects.get(is_associate=assoc, has_associate=node, association_type=aat)#
                        assoc.state = association.state
                    aat.assoc_list = assoc_list
                    aats.append(aat)
            node.aats = aats

    return render_to_response("work/your_projects.html", {
        "roots": roots,
        "help": get_help("your_projects"),
        "agent": agent,
        "agent_form": agent_form,
        "managed_projects": managed_projects,
        "join_projects": join_projects,
    }, context_instance=RequestContext(request))


@login_required
def create_your_project(request):
    user_agent = get_agent(request)
    if not user_agent or not user_agent.is_active_freedom_coop_member:
        return render_to_response('work/no_permission.html')
    if request.method == "POST":
        pro_form = ProjectCreateForm(request.POST)
        agn_form = AgentCreateForm(request.POST)
        if pro_form.is_valid() and agn_form.is_valid():
            agent = agn_form.save(commit=False)
            agent.created_by=request.user
            agent.is_context=True
            agent.save()
            project = pro_form.save(commit=False)
            project.agent = agent
            project.save()

            association_type = AgentAssociationType.objects.get(identifier="manager")
            fc_aa = AgentAssociation(
                is_associate=user_agent,
                has_associate=agent,
                association_type=association_type,
                state="active",
                )
            fc_aa.save()

            fc = EconomicAgent.objects.freedom_coop()
            association_type = AgentAssociationType.objects.get(identifier="child")
            fc_aa = AgentAssociation(
                is_associate=agent,
                has_associate=fc,
                association_type=association_type,
                state="active",
                )
            fc_aa.save()

            return HttpResponseRedirect('/%s/%s/'
                % ('work/agent', agent.id))
    return HttpResponseRedirect("/work/your-projects/")


# bum2
@login_required
def members_agent(request, agent_id):
    #import pdb; pdb.set_trace()
    agent = get_object_or_404(EconomicAgent, id=agent_id)
    user_agent = get_agent(request)
    if not user_agent or not user_agent.is_participant or not user_agent.is_active_freedom_coop_member:
        return render_to_response('work/no_permission.html')

    user_is_agent = False
    if agent == user_agent:
        user_is_agent = True
    try:
        project = agent.project
    except:
        project = False

    if project:
        init = {"joining_style": project.joining_style, "visibility": project.visibility, "fobi_slug": project.fobi_slug }
        change_form = ProjectCreateForm(instance=agent, initial=init)
    else:
        change_form = ProjectCreateForm(instance=agent) #AgentCreateForm(instance=agent)

    nav_form = InternalExchangeNavForm(data=request.POST or None)
    if agent:
        if request.method == "POST":
            #import pdb; pdb.set_trace()
            if nav_form.is_valid():
                data = nav_form.cleaned_data
                ext = data["exchange_type"]
            return HttpResponseRedirect('/%s/%s/%s/%s/'
                % ('work/exchange', ext.id, 0, agent.id))
    user_form = None

    if not agent.username():
        init = {"username": agent.nick,}
        user_form = UserCreationForm(initial=init)
    has_associations = agent.all_has_associates()
    is_associated_with = agent.all_is_associates()

    headings = []
    member_hours_recent = []
    member_hours_stats = []
    individual_stats = []
    member_hours_roles = []
    roles_height = 400

    membership_request = agent.membership_request()
    entries = []
    fobi_name = 'None'

    if agent.is_individual():
        contributions = agent.given_events.filter(is_contribution=True)
        agents_stats = {}
        for ce in contributions:
            agents_stats.setdefault(ce.resource_type, Decimal("0"))
            agents_stats[ce.resource_type] += ce.quantity
        for key, value in agents_stats.items():
            individual_stats.append((key, value))
        individual_stats.sort(lambda x, y: cmp(y[1], x[1]))

    elif agent.is_context_agent():
        try:
          fobi_name = get_object_or_404(FormEntry, slug=agent.project.fobi_slug)
          entries = agent.project.join_requests.filter(agent__isnull=True)
        except:
          entries = []

        subs = agent.with_all_sub_agents()
        end = datetime.date.today()
        #end = end - datetime.timedelta(days=77)
        start =  end - datetime.timedelta(days=60)
        events = EconomicEvent.objects.filter(
            event_type__relationship="work",
            context_agent__in=subs,
            event_date__range=(start, end))

        if events:
            agents_stats = {}
            for event in events:
                agents_stats.setdefault(event.from_agent.name, Decimal("0"))
                agents_stats[event.from_agent.name] += event.quantity
            for key, value in agents_stats.items():
                member_hours_recent.append((key, value))
            member_hours_recent.sort(lambda x, y: cmp(y[1], x[1]))

        #import pdb; pdb.set_trace()

        ces = CachedEventSummary.objects.filter(
            event_type__relationship="work",
            context_agent__in=subs)

        if ces.count():
            agents_stats = {}
            for ce in ces:
                agents_stats.setdefault(ce.agent.name, Decimal("0"))
                agents_stats[ce.agent.name] += ce.quantity
            for key, value in agents_stats.items():
                member_hours_stats.append((key, value))
            member_hours_stats.sort(lambda x, y: cmp(y[1], x[1]))

            agents_roles = {}
            roles = [ce.quantity_label() for ce in ces]
            roles = list(set(roles))
            for ce in ces:
                if ce.quantity:
                    name = ce.agent.name
                    row = [name, ]
                    for i in range(0, len(roles)):
                        row.append(Decimal("0.0"))
                        key = ce.agent.name
                    agents_roles.setdefault(key, row)
                    idx = roles.index(ce.quantity_label()) + 1
                    agents_roles[key][idx] += ce.quantity
            headings = ["Member",]
            headings.extend(roles)
            for row in agents_roles.values():
                member_hours_roles.append(row)
            member_hours_roles.sort(lambda x, y: cmp(x[0], y[0]))
            roles_height = len(member_hours_roles) * 20

    return render_to_response("work/members_agent.html", {
        "agent": agent,
        "membership_request": membership_request,
        "photo_size": (128, 128),
        "change_form": change_form,
        "user_form": user_form,
        "nav_form": nav_form,
        "user_agent": user_agent,
        "user_is_agent": user_is_agent,
        "has_associations": has_associations,
        "is_associated_with": is_associated_with,
        "headings": headings,
        "member_hours_recent": member_hours_recent,
        "member_hours_stats": member_hours_stats,
        "member_hours_roles": member_hours_roles,
        "individual_stats": individual_stats,
        "roles_height": roles_height,
        "help": get_help("members_agent"),
        "form_entries": entries,
        "fobi_name": fobi_name,
    }, context_instance=RequestContext(request))


@login_required
def change_your_project(request, agent_id):
    agent = get_object_or_404(EconomicAgent, id=agent_id)
    user_agent = get_agent(request)
    if not user_agent:
        return render_to_response('work/no_permission.html')
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        try:
          project = agent.project
        except:
          project = False
        if not project:
          pro_form = ProjectCreateForm(request.POST)
          if pro_form.is_valid():
            project = pro_form.save(commit=False)
            project.agent = agent
            project.save()
        else:
          pro_form = ProjectCreateForm(instance=project, data=request.POST or None)
          agn_form = AgentCreateForm(instance=agent, data=request.POST or None)
        if pro_form.is_valid() and agn_form.is_valid():
            project = pro_form.save()
            data = agn_form.cleaned_data
            url = data["url"]
            if url and not url[0:3] == "http":
              data["url"] = "http://" + url
              agent.url = data["url"]
            #agent.project = project
            agent = agn_form.save(commit=False)
            agent.is_context = True
            agent.save()

    return HttpResponseRedirect('/%s/%s/'
        % ('work/agent', agent.id))



from fobi.dynamic import assemble_form_class
from fobi.settings import GET_PARAM_INITIAL_DATA, DEBUG
from fobi.constants import (
    CALLBACK_BEFORE_FORM_VALIDATION,
    CALLBACK_FORM_VALID_BEFORE_SUBMIT_PLUGIN_FORM_DATA,
    CALLBACK_FORM_VALID, CALLBACK_FORM_VALID_AFTER_FORM_HANDLERS,
    CALLBACK_FORM_INVALID
)
from fobi.base import (
    fire_form_callbacks, run_form_handlers, form_element_plugin_registry,
    form_handler_plugin_registry, submit_plugin_form_data, get_theme,
    get_processed_form_data
)
#from fobi.base import (
#    FormHandlerPlugin, form_handler_plugin_registry, get_processed_form_data
#)

import simplejson as json
from django.utils.html import escape, escapejs

def joinaproject_request(request, form_slug = False):
    join_form = JoinRequestForm(data=request.POST or None)
    fobi_form = False
    cleaned_data = False
    form = False
    if form_slug:
      project = Project.objects.get(fobi_slug=form_slug)

      if request.user.is_authenticated() and request.user.agent.agent.is_active_freedom_coop_member() or request.user.is_staff():
        return joinaproject_request_internal(request, project.agent.id)

      fobi_slug = project.fobi_slug
      form_entry = FormEntry.objects.get(slug=fobi_slug)
      form_element_entries = form_entry.formelemententry_set.all()[:]
      form_entry.project = project

      # This is where the most of the magic happens. Our form is being built
      # dynamically.
      FormClass = assemble_form_class(
          form_entry,
          form_element_entries = form_element_entries,
          request = request
      )


    if request.method == "POST":
        #import pdb; pdb.set_trace()
        fobi_form = FormClass(request.POST, request.FILES)
        #form_element_entries = form_entry.formelemententry_set.all()[:]
        #field_name_to_label_map, cleaned_data = get_processed_form_data(
        #    fobi_form, form_element_entries,
        #)

        if join_form.is_valid():
            human = True
            data = join_form.cleaned_data
            type_of_user = data["type_of_user"]
            name = data["name"]
            surname = data["surname"]
            #description = data["description"]

            jn_req = join_form.save(commit=False)
            jn_req.project = project
            jn_req.save()

            #request.POST._mutable = True
            #request.POST['join_request'] = str(jn_req.pk)

            if form_slug:
              #fobi_form = FormClass(request.POST, request.FILES)

              # Fire pre form validation callbacks
              fire_form_callbacks(form_entry=form_entry, request=request, form=fobi_form, stage=CALLBACK_BEFORE_FORM_VALIDATION)
              if fobi_form.is_valid():
                #return HttpResponseRedirect('/%s/' % ('joinaprojectthanks'))

                # Fire form valid callbacks, before handling submitted plugin form data.
                fobi_form = fire_form_callbacks(
                    form_entry = form_entry,
                    request = request,
                    form = fobi_form,
                    stage = CALLBACK_FORM_VALID_BEFORE_SUBMIT_PLUGIN_FORM_DATA
                )

                # Fire plugin processors
                fobi_form = submit_plugin_form_data(form_entry=form_entry,
                                               request=request, form=fobi_form)

                # Fire form valid callbacks
                fobi_form = fire_form_callbacks(form_entry=form_entry,
                                           request=request, form=fobi_form,
                                           stage=CALLBACK_FORM_VALID)

                '''# Run all handlers
                handler_responses, handler_errors = run_form_handlers(
                    form_entry = form_entry,
                    request = request,
                    form = fobi_form,
                    form_element_entries = form_element_entries
                )

                # Warning that not everything went ok.
                if handler_errors:
                    for handler_error in handler_errors:
                        messages.warning(
                            request,
                            _("Error occured: {0}."
                              "").format(handler_error)
                        )
                '''

                # Fire post handler callbacks
                fire_form_callbacks(
                    form_entry = form_entry,
                    request = request,
                    form = fobi_form,
                    stage = CALLBACK_FORM_VALID_AFTER_FORM_HANDLERS
                    )

                #messages.info(
                #    request,
                #    _("Form {0} was submitted successfully.").format(form_entry.name)
                #)

                field_name_to_label_map, cleaned_data = get_processed_form_data(
                    fobi_form,
                    form_element_entries
                )

                #for key, value in cleaned_data.items():
                #    if key == "join_request": #isinstance(value, (datetime.datetime, datetime.date)):
                #        cleaned_data[key] = jn_req.pk #value.isoformat() if hasattr(value, 'isoformat') else value

                saved_form_data_entry = SavedFormDataEntry(
                    form_entry = form_entry,
                    user = request.user if request.user and request.user.pk else None,
                    form_data_headers = json.dumps(field_name_to_label_map),
                    saved_data = json.dumps(cleaned_data)
                    )
                saved_form_data_entry.save()
                jn = JoinRequest.objects.get(pk=jn_req.pk)
                jn.fobi_data = saved_form_data_entry
                #messages.info(
                #    request,
                #    _("JoinRequest {0} was submitted successfully. {1}").format(jn.fobi_data, saved_form_data_entry.pk)
                #)
                jn.save()

            # add relation candidate
            #ass_type = get_object_or_404(AgentAssociationType, identifier="participant")
            #if ass_type:
            #    fc_aa = AgentAssociation(
            #        is_associate=jn_req.agent,
            #        has_associate=jn_req.project.agent,
            #        association_type=ass_type,
            #        state="potential",
            #        )
            #    fc_aa.save()

            event_type = EventType.objects.get(relationship="todo")
            description = "Create an Agent and User for the Join Request from "
            description += name
            join_url = get_url_starter() + "/work/agent/" + str(jn_req.project.agent.id) +"/join-requests/"
            context_agent = jn_req.project.agent #EconomicAgent.objects.get(name__icontains="Membership Request")
            resource_types = EconomicResourceType.objects.filter(behavior="work")
            rts = resource_types.filter(
                Q(name__icontains="Admin")|
                Q(name__icontains="Coop")|
                Q(name__icontains="Work"))
            if rts:
                rt = rts[0]
            else:
                rt = resource_types[0]

            task = Commitment(
                event_type=event_type,
                description=description,
                resource_type=rt,
                context_agent=context_agent,
                url=join_url,
                due_date=datetime.date.today(),
                quantity=Decimal("1")
                )
            task.save()


            if notification:
                managers = jn_req.project.agent.managers()
                users = []
                for manager in managers:
                  if manager.user():
                    users.append(manager.user().user)
                if users:
                    site_name = get_site_name()
                    notification.send(
                        users,
                        "work_join_request",
                        {"name": name,
                        "surname": surname,
                        "type_of_user": type_of_user,
                        "description": description,
                        "site_name": site_name,
                        "join_url": join_url,
                        "context_agent": context_agent,
                        }
                    )

            return HttpResponseRedirect('/%s/'
                % ('joinaproject-thanks'))


    kwargs = {'initial': {'fobi_initial_data':form_slug} }
    fobi_form = FormClass(**kwargs)

    return render_to_response("work/joinaproject_request.html", {
        "help": get_help("work_join_request"),
        "join_form": join_form,
        "fobi_form": fobi_form,
        "project": project,
        "post": escapejs(json.dumps(request.POST)),
    }, context_instance=RequestContext(request))


@login_required
def joinaproject_request_internal(request, agent_id = False):
    proj_agent = get_object_or_404(EconomicAgent, id=agent_id)
    project = proj_agent.project
    form_slug = project.fobi_slug
    join_form = JoinRequestInternalForm(data=request.POST or None)
    fobi_form = False
    cleaned_data = False
    form = False
    if form_slug:
      #project = Project.objects.get(fobi_slug=form_slug)
      fobi_slug = project.fobi_slug
      form_entry = FormEntry.objects.get(slug=fobi_slug)
      form_element_entries = form_entry.formelemententry_set.all()[:]
      #form_entry.project = project

      # This is where the most of the magic happens. Our form is being built
      # dynamically.
      FormClass = assemble_form_class(
          form_entry,
          form_element_entries = form_element_entries,
          request = request
      )
    else:
      return render_to_response('work/no_permission.html')

    if request.method == "POST":
        #import pdb; pdb.set_trace()
        fobi_form = FormClass(request.POST, request.FILES)
        #form_element_entries = form_entry.formelemententry_set.all()[:]
        #field_name_to_label_map, cleaned_data = get_processed_form_data(
        #    fobi_form, form_element_entries,
        #)

        if join_form.is_valid():
            human = True
            data = join_form.cleaned_data
            type_of_user = proj_agent.agent_type #data["type_of_user"]
            name = proj_agent.name #data["name"]
            #surname = proj_agent.surname #data["surname"]
            #description = data["description"]

            jn_req = join_form.save(commit=False)
            jn_req.project = project
            if request.user.agent.agent:
              jn_req.agent = request.user.agent.agent
            jn_req.save()

            #request.POST._mutable = True
            #request.POST['join_request'] = str(jn_req.pk)

            if form_slug:
              #fobi_form = FormClass(request.POST, request.FILES)

              # Fire pre form validation callbacks
              fire_form_callbacks(form_entry=form_entry, request=request, form=fobi_form, stage=CALLBACK_BEFORE_FORM_VALIDATION)
              if fobi_form.is_valid():
                #return HttpResponseRedirect('/%s/' % ('joinaprojectthanks'))

                # Fire form valid callbacks, before handling submitted plugin form data.
                fobi_form = fire_form_callbacks(
                    form_entry = form_entry,
                    request = request,
                    form = fobi_form,
                    stage = CALLBACK_FORM_VALID_BEFORE_SUBMIT_PLUGIN_FORM_DATA
                )

                # Fire plugin processors
                fobi_form = submit_plugin_form_data(form_entry=form_entry,
                                               request=request, form=fobi_form)

                # Fire form valid callbacks
                fobi_form = fire_form_callbacks(form_entry=form_entry,
                                           request=request, form=fobi_form,
                                           stage=CALLBACK_FORM_VALID)

                '''# Run all handlers
                handler_responses, handler_errors = run_form_handlers(
                    form_entry = form_entry,
                    request = request,
                    form = fobi_form,
                    form_element_entries = form_element_entries
                )

                # Warning that not everything went ok.
                if handler_errors:
                    for handler_error in handler_errors:
                        messages.warning(
                            request,
                            _("Error occured: {0}."
                              "").format(handler_error)
                        )
                '''

                # Fire post handler callbacks
                fire_form_callbacks(
                    form_entry = form_entry,
                    request = request,
                    form = fobi_form,
                    stage = CALLBACK_FORM_VALID_AFTER_FORM_HANDLERS
                    )

                #messages.info(
                #    request,
                #    _("Form {0} was submitted successfully.").format(form_entry.name)
                #)

                field_name_to_label_map, cleaned_data = get_processed_form_data(
                    fobi_form,
                    form_element_entries
                )

                saved_form_data_entry = SavedFormDataEntry(
                    form_entry = form_entry,
                    user = request.user if request.user and request.user.pk else None,
                    form_data_headers = json.dumps(field_name_to_label_map),
                    saved_data = json.dumps(cleaned_data)
                    )
                saved_form_data_entry.save()
                jn = JoinRequest.objects.get(pk=jn_req.pk)
                jn.fobi_data = saved_form_data_entry
                #messages.info(
                #    request,
                #    _("JoinRequest {0} was submitted successfully. {1}").format(jn.fobi_data, saved_form_data_entry.pk)
                #)
                jn.save()

            # add relation candidate
            if jn_req.agent:
                ass_type = get_object_or_404(AgentAssociationType, identifier="participant")
                if ass_type:
                  fc_aa = AgentAssociation(
                    is_associate=jn_req.agent,
                    has_associate=jn_req.project.agent,
                    association_type=ass_type,
                    state="potential",
                    )
                  fc_aa.save()

            description = "A new Join Request from OCP user "
            description += name
            join_url = ''

            '''event_type = EventType.objects.get(relationship="todo")
            join_url = get_url_starter() + "/work/agent/" + str(jn_req.project.agent.id) +"/join-requests/"
            context_agent = jn_req.project.agent #EconomicAgent.objects.get(name__icontains="Membership Request")
            resource_types = EconomicResourceType.objects.filter(behavior="work")
            rts = resource_types.filter(
                Q(name__icontains="Admin")|
                Q(name__icontains="Coop")|
                Q(name__icontains="Work"))
            if rts:
                rt = rts[0]
            else:
                rt = resource_types[0]

            task = Commitment(
                event_type=event_type,
                description=description,
                resource_type=rt,
                context_agent=context_agent,
                url=join_url,
                due_date=datetime.date.today(),
                quantity=Decimal("1")
                )
            task.save()'''


            if notification:
                managers = jn_req.project.agent.managers()
                users = []
                for manager in managers:
                  if manager.user():
                    users.append(manager.user().user)
                if users:
                    site_name = get_site_name()
                    notification.send(
                        users,
                        "work_join_request",
                        {"name": name,
                        #"surname": surname,
                        "type_of_user": type_of_user,
                        "description": description,
                        "site_name": site_name,
                        "join_url": join_url,
                        "context_agent": proj_agent,
                        }
                    )

            return HttpResponseRedirect('/%s/'
                % ('work/your-projects'))


    kwargs = {'initial': {'fobi_initial_data':form_slug} }
    fobi_form = FormClass(**kwargs)

    return render_to_response("work/joinaproject_request_internal.html", {
        "help": get_help("work_join_request_internal"),
        "join_form": join_form,
        "fobi_form": fobi_form,
        "project": project,
        "post": escapejs(json.dumps(request.POST)),
    }, context_instance=RequestContext(request))



@login_required
def join_requests(request, agent_id):
    state = "new"
    state_form = RequestStateForm(
        initial={"state": "new",},
        data=request.POST or None)

    if request.method == "POST":
        if state_form.is_valid():
            data = state_form.cleaned_data
            state = data["state"]

    agent = EconomicAgent.objects.get(pk=agent_id)
    project = agent.project
    requests =  JoinRequest.objects.filter(state=state, project=project)
    agent_form = JoinAgentSelectionForm()

    fobi_slug = project.fobi_slug
    fobi_headers = []
    fobi_keys = []

    if fobi_slug and requests:
        form_entry = FormEntry.objects.get(slug=fobi_slug)
        req = requests[0]
        if req.fobi_data and req.fobi_data._default_manager:
            req.entries = req.fobi_data._default_manager.filter(pk=req.fobi_data.pk).select_related('form_entry')
            entry = req.entries[0]
            form_headers = json.loads(entry.form_data_headers)
            for val in form_headers:
                fobi_headers.append(form_headers[val])
                fobi_keys.append(val)

        for req in requests:
            req.entries = req.fobi_data._default_manager.filter(pk=req.fobi_data.pk).select_related('form_entry')
            entry = req.entries[0]
            req.data = json.loads(entry.saved_data)
            req.items = req.data.items()
            req.items_data = []
            for key in fobi_keys:
              req.items_data.append(req.data.get(key))

    return render_to_response("work/join_requests.html", {
        "help": get_help("join_requests"),
        "requests": requests,
        "state_form": state_form,
        "state": state,
        "agent_form": agent_form,
        "project": project,
        "fobi_headers": fobi_headers,
    }, context_instance=RequestContext(request))


'''@login_required
def join_request(request, join_request_id):
    user_agent = get_agent(request)
    if not user_agent:
        return render_to_response('work/no_permission.html')
    mbr_req = get_object_or_404(JoinRequest, pk=join_request_id)
    init = {
        "name": " ".join([mbr_req.name, mbr_req.surname]),
        "nick": mbr_req.requested_username,
        #"description": mbr_req.description,
        "email": mbr_req.email_address,
        "url": mbr_req.website,
        }
    if mbr_req.type_of_user == "individual":
        at = AgentType.objects.filter(party_type="individual")
        if at:
            at = at[0]
            init["agent_type"] = at
    agent_form = AgentCreateForm(initial=init)
    nicks = '~'.join([
        agt.nick for agt in EconomicAgent.objects.all()])
    return render_to_response("work/join_request.html", {
        "help": get_help("join_request"),
        "mbr_req": mbr_req,
        "agent_form": agent_form,
        "user_agent": user_agent,
        "nicks": nicks,
    }, context_instance=RequestContext(request))
'''

@login_required
def decline_request(request, join_request_id):
    mbr_req = get_object_or_404(JoinRequest, pk=join_request_id)
    mbr_req.state = "declined"
    mbr_req.save()
    if mbr_req.agent and mbr_req.project:
        # modify relation to active
        ass_type = AgentAssociationType.objects.get(identifier="participant")
        ass = AgentAssociation.objects.get(is_associate=mbr_req.agent, has_associate=mbr_req.project.agent, association_type=ass_type)
        ass.state = "potential"
        ass.save()
    return HttpResponseRedirect('/%s/%s/%s/'
        % ('work/agent', mbr_req.project.agent.id, 'join-requests'))

@login_required
def undecline_request(request, join_request_id):
    mbr_req = get_object_or_404(JoinRequest, pk=join_request_id)
    mbr_req.state = "new"
    mbr_req.save()
    return HttpResponseRedirect('/%s/%s/%s/'
        % ('work/agent', mbr_req.project.agent.id, 'join-requests'))

@login_required
def delete_request(request, join_request_id):
    mbr_req = get_object_or_404(JoinRequest, pk=join_request_id)
    mbr_req.delete()
    if mbr_req.agent:
      pass # delete user and agent?

    return HttpResponseRedirect('/%s/%s/%s/'
        % ('work/agent', mbr_req.project.agent.id, 'join-requests'))

@login_required
def accept_request(request, join_request_id):
    mbr_req = get_object_or_404(JoinRequest, pk=join_request_id)
    mbr_req.state = "accepted"
    mbr_req.save()

    # modify relation to active
    association_type = AgentAssociationType.objects.get(identifier="participant")
    association = AgentAssociation.objects.get(is_associate=mbr_req.agent, has_associate=mbr_req.project.agent, association_type=association_type)
    association.state = "active"
    association.save()

    return HttpResponseRedirect('/%s/%s/%s/'
        % ('work/agent', mbr_req.project.agent.id, 'join-requests'))


from itertools import chain

@login_required
def create_account_for_join_request(request, join_request_id):
    if request.method == "POST":
        jn_req = get_object_or_404(JoinRequest, pk=join_request_id)
        #import pdb; pdb.set_trace()
        form = ProjectAgentCreateForm(prefix=jn_req.form_prefix(), data=request.POST or None)
        if form.is_valid():
            data = form.cleaned_data
            agent = form.save(commit=False)
            agent.created_by=request.user
            if not agent.is_individual():
                agent.is_context=True
            agent.save()
            jn_req.agent = agent
            jn_req.save()
            project = jn_req.project
            # add relation candidate
            ass_type = get_object_or_404(AgentAssociationType, identifier="participant")
            if ass_type:
                aa = AgentAssociation(
                    is_associate=agent,
                    has_associate=project.agent,
                    association_type=ass_type,
                    state="potential",
                    )
                aa.save()
            password = data["password"]
            if password:
                username = data["nick"]
                email = data["email"]
                if username:
                    user = User(
                        username=username,
                        email=email,
                        )
                    user.set_password(password)
                    user.save()
                    au = AgentUser(
                        agent = agent,
                        user = user)
                    au.save()
                    #agent.request_faircoin_address()

                    name = data["name"]
                    if notification:
                        managers = project.agent.managers()
                        users = [agent.user().user,]
                        for manager in managers:
                            if manager.user():
                                users.append(manager.user().user)
                        #users = User.objects.filter(is_staff=True)
                        if users:
                            #allusers = chain(users, agent)
                            #users = list(users)
                            #users.append(agent.user)
                            site_name = get_site_name()
                            notification.send(
                                users,
                                "work_new_account",
                                {"name": name,
                                "username": username,
                                "password": password,
                                "site_name": site_name,
                                "context_agent": project.agent,
                                }
                            )

            return HttpResponseRedirect('/%s/%s/%s/'
                % ('work/agent', project.agent.id, 'join-requests'))

    return HttpResponseRedirect('/%s/%s/%s/'
        % ('work/agent', jn_req.project.agent.id, 'join-requests'))

def validate_nick(request):
    #import pdb; pdb.set_trace()
    answer = True
    error = ""
    data = request.GET
    values = data.values()
    if values:
        nick = values[0]
        try:
            user = EconomicAgent.objects.get(nick=nick)
            error = "ID already taken"
        except EconomicAgent.DoesNotExist:
            pass
        if not error:
            username = nick
            try:
                user = User.objects.get(username=username)
                error = "Username already taken"
            except User.DoesNotExist:
                pass
            if not error:
                val = validators.RegexValidator(r'^[\w.@+-]+$',
                                            _('Enter a valid username. '
                                                'This value may contain only letters, numbers '
                                               'and @/./+/-/_ characters.'), 'invalid')
                try:
                    error = val(username)
                except ValidationError:
                    error = "Error: May only contain letters, numbers, and @/./+/-/_ characters."

    if error:
        answer = error
    response = simplejson.dumps(answer, ensure_ascii=False)
    return HttpResponse(response, content_type="text/json-comment-filtered")

def validate_username(request):
    #import pdb; pdb.set_trace()
    answer = True
    error = ""
    data = request.GET
    values = data.values()
    if values:
        username = values[0]
        try:
            user = User.objects.get(username=username)
            error = "Username already taken"
        except User.DoesNotExist:
            pass
        if not error:
            val = validators.RegexValidator(r'^[\w.@+-]+$',
                                        _('Enter a valid username. '
                                            'This value may contain only letters, numbers '
                                            'and @/./+/-/_ characters.'), 'invalid')
            error = val(username)
    if error:
        answer = error
    response = simplejson.dumps(answer, ensure_ascii=False)
    return HttpResponse(response, content_type="text/json-comment-filtered")

@login_required
def connect_agent_to_join_request(request, agent_id, join_request_id):
    mbr_req = get_object_or_404(JoinRequest, pk=join_request_id)
    project_agent = get_object_or_404(EconomicAgent, pk=agent_id)
    if request.method == "POST":
        agent_form = JoinAgentSelectionForm(data=request.POST)
        if agent_form.is_valid():
            data = agent_form.cleaned_data
            #import pdb; pdb.set_trace()
            agent = data["created_agent"]
            mbr_req.agent=agent
            mbr_req.state = "new"
            mbr_req.save()

    return HttpResponseRedirect('/%s/%s/%s/'
        % ('work/agent', project_agent.id, 'join-requests'))

from six import text_type, PY3
from django.utils.encoding import force_text

def safe_text(text):
    """
    Safe text (encode).

    :return str:
    """
    if PY3:
        return force_text(text, encoding='utf-8')
    else:
        return force_text(text, encoding='utf-8').encode('utf-8')

def two_dicts_to_string(headers, data, html_element1='th', html_element2='td'):
    """
    Takes two dictionaries, assuming one contains a mapping keys to titles
    and another keys to data. Joins as string and returns wrapped into
    HTML "p" tag.
    """
    formatted_data = [
        (value, data.get(key, '')) for key, value in list(headers.items())
        ]
    return "".join(
        ["<tr><{0}>{1}</{2}><{3}>{4}</{5}></tr>".format(html_element1, safe_text(key), html_element1, html_element2,
                                      safe_text(value), html_element2)
         for key, value in formatted_data]
        )

@login_required
def project_feedback(request, agent_id, join_request_id):
    user_agent = get_agent(request)
    agent = get_object_or_404(EconomicAgent, pk=agent_id)
    jn_req = get_object_or_404(JoinRequest, pk=join_request_id)
    project = agent.project
    allowed = False
    if user_agent and jn_req:
      if user_agent.is_staff() or user_agent in agent.managers():
        allowed = True
      elif jn_req.agent == request.user.agent.agent: #in user_agent.joinaproject_requests():
        allowed = True
    if not allowed:
        return render_to_response('work/no_permission.html')

    fobi_slug = project.fobi_slug
    fobi_headers = []
    fobi_keys = []

    if fobi_slug:
        form_entry = FormEntry.objects.get(slug=fobi_slug)
        #req = jn_req
        if jn_req.fobi_data:
            jn_req.entries = jn_req.fobi_data._default_manager.filter(pk=jn_req.fobi_data.pk) #.select_related('form_entry')
            jn_req.entry = jn_req.entries[0]
            jn_req.form_headers = json.loads(jn_req.entry.form_data_headers)
            for val in jn_req.form_headers:
                fobi_headers.append(jn_req.form_headers[val])
                fobi_keys.append(val)

            jn_req.data = json.loads(jn_req.entry.saved_data)
            #jn_req.tworows = two_dicts_to_string(jn_req.form_headers, jn_req.data, 'th', 'td')
            jn_req.items = jn_req.data.items()
            jn_req.items_data = []
            for key in fobi_keys:
              jn_req.items_data.append({"key": jn_req.form_headers[key], "val": jn_req.data.get(key)})

    return render_to_response("work/join_request_with_comments.html", {
        "help": get_help("project_feedback"),
        "jn_req": jn_req,
        "user_agent": user_agent,
        "agent": agent,
        "fobi_headers": fobi_headers,
    }, context_instance=RequestContext(request))

'''
@login_required
def create_project_user_and_agent(request, agent_id):
    #import pdb; pdb.set_trace()
    project_agent = get_object_or_404(EconomicAgent, id=agent_id)
    if not project_agent.managers: # or not request.user.agent.agent in project_agent.managers:
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
        if agent_form.is_valid():
            nick = request.POST.get("nick")
            description = request.POST.get("description")
            url = request.POST.get("url")
            address = request.POST.get("address")
            email = request.POST.get("email")
            agent_type_id = request.POST.get("agent_type")
            errors = False
            password1 = request.POST.get("password1")
            password2 = request.POST.get("password2")
            username = request.POST.get("username")
            first_name = request.POST.get("first_name")
            last_name = request.POST.get("last_name")  or ""
            if password1:
                if password1 != password2:
                    errors = True
                if not username:
                    errors = True
                user_form.is_valid()
            if not errors:
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
                    if nick and first_name:
                        try:
                            agent = EconomicAgent.objects.get(nick=nick)
                            errors = True
                        except EconomicAgent.DoesNotExist:
                            pass
                    else:
                        errors = True
                    if not errors:
                        name = " ".join([first_name, last_name])
                        agent_type = AgentType.objects.get(id=agent_type_id)
                        agent = EconomicAgent(
                            nick = nick,
                            name = name,
                            description = description,
                            url = url,
                            address = address,
                            agent_type = agent_type,
                        )
                if not errors:
                    if user_form.is_valid():
                        agent.created_by=request.user
                        agent.save()
                        user = user_form.save(commit=False)
                        user.first_name = request.POST.get("first_name")
                        user.last_name = request.POST.get("last_name")
                        user.email = request.POST.get("email")
                        user.save()
                        au = AgentUser(
                            agent = agent,
                            user = user)
                        au.save()
                        return HttpResponseRedirect('/%s/%s/'
                            % ('accounting/agent', agent.id))

    return render_to_response("work/create_project_user_and_agent.html", {
        "user_form": user_form,
        "agent_form": agent_form,
        "agent_selection_form": agent_selection_form,
    }, context_instance=RequestContext(request))

'''
