import sys
import datetime
from decimal import *
from collections import OrderedDict

import bleach
from captcha.fields import CaptchaField

from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from valuenetwork.valueaccounting.models import *
from work.models import *
from valuenetwork.valueaccounting.forms import *


class ProjectAgentCreateForm(forms.ModelForm):
    name = forms.CharField(widget=forms.TextInput(attrs={'class': 'required-field input-xlarge',}))
    nick = forms.CharField(
        label="ID",
        help_text="Must be unique, and no more than 32 characters",
        widget=forms.TextInput(attrs={'class': 'nick required-field',}))
    email = forms.EmailField(required=False, widget=forms.TextInput(attrs={'class': 'email input-xxlarge',}))
    #address = forms.CharField(
    #    required=False,
    #    label="Work location",
    #    help_text="Enter address for a new work location. Otherwise, select existing location on map.",
    #    widget=forms.TextInput(attrs={'class': 'input-xxlarge',}))
    url = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'url input-xxlarge',}))
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'input-xxlarge',}))
    agent_type = forms.ModelChoiceField(
        queryset=AgentType.objects.all(),
        empty_label=None,
        widget=forms.Select(
        attrs={'class': 'chzn-select'}))
    #is_context = forms.BooleanField(
    #    required=False,
    #    label="Is a context agent",
    #    widget=forms.CheckboxInput())
    password = forms.CharField(label=_("Password"),
        help_text=_("Login password"),
        widget=forms.PasswordInput(attrs={'class': 'password',}))

    class Meta:
        model = EconomicAgent
        #removed address and is_context
        fields = ('name', 'nick', 'agent_type', 'description', 'url', 'email')


class UploadAgentForm(forms.ModelForm):
    photo_url = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'url input-xxlarge',}))

    class Meta:
        model = EconomicAgent
        fields = ('photo', 'photo_url')


class SkillSuggestionForm(forms.ModelForm):
    skill = forms.CharField(
        label = "Other",
        help_text = _("Your skill suggestions will be sent to Freedom Coop Admins"),
        )

    class Meta:
        model = SkillSuggestion
        fields = ('skill',)


class MembershipRequestForm(forms.ModelForm):
    captcha = CaptchaField()

    class Meta:
        model = MembershipRequest
        exclude = ('agent',)

    def clean(self):
        #import pdb; pdb.set_trace()
        data = super(MembershipRequestForm, self).clean()
        type_of_membership = data["type_of_membership"]
        number_of_shares = data["number_of_shares"]
        if type_of_membership == "collective":
            if int(number_of_shares) < 2:
                msg = "Number of shares must be at least 2 for a collective."
                self.add_error('number_of_shares', msg)

    def _clean_fields(self):
        super(MembershipRequestForm, self)._clean_fields()
        for name, value in self.cleaned_data.items():
            self.cleaned_data[name] = bleach.clean(value)


class WorkProjectSelectionFormOptional(forms.Form):
    context_agent = forms.ChoiceField()

    def __init__(self, context_agents, *args, **kwargs):
        super(WorkProjectSelectionFormOptional, self).__init__(*args, **kwargs)
        self.fields["context_agent"].choices = [('', '--All My Projects--')] + [(proj.id, proj.name) for proj in context_agents]

class WorkTodoForm(forms.ModelForm):
    from_agent = forms.ModelChoiceField(
        required=False,
        #queryset=EconomicAgent.objects.individuals(),
        queryset=EconomicAgent.objects.with_user(),
        label="Assigned to",
        widget=forms.Select(
            attrs={'class': 'chzn-select'}))
    resource_type = WorkModelChoiceField(
        queryset=EconomicResourceType.objects.filter(behavior="work"),
        label="Type of work",
        empty_label=None,
        widget=forms.Select(
            attrs={'class': 'chzn-select'}))
    context_agent = forms.ModelChoiceField(
        queryset=EconomicAgent.objects.context_agents(),
        label=_("Context"),
        empty_label=None,
        widget=forms.Select(attrs={'class': 'chzn-select'}))
    due_date = forms.DateField(widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'todo-description input-xlarge',}))
    url = forms.URLField(required=False, widget=forms.TextInput(attrs={'class': 'url input-xlarge',}))

    class Meta:
        model = Commitment
        fields = ('from_agent', 'context_agent', 'resource_type', 'due_date', 'description', 'url')

    def __init__(self, agent, pattern=None, *args, **kwargs): #agent is posting agent
        super(WorkTodoForm, self).__init__(*args, **kwargs)
        contexts = agent.related_contexts()
        self.fields["context_agent"].choices = list(set([(ct.id, ct) for ct in contexts]))
        peeps = [agent,]
        from_agent_choices = [('', 'Unassigned'), (agent.id, agent),]
        #import pdb; pdb.set_trace()
        for context in contexts:
            if agent.is_manager_of(context):
                peeps.extend(context.task_assignment_candidates())
        if len(peeps) > 1:
            peeps = list(OrderedDict.fromkeys(peeps))
        from_agent_choices = [('', 'Unassigned')] + [(peep.id, peep) for peep in peeps]

        self.fields["from_agent"].choices = from_agent_choices
        if pattern:
            self.pattern = pattern
            self.fields["resource_type"].choices = [(rt.id, rt) for rt in pattern.todo_resource_types()]


class ProjectCreateForm(AgentCreateForm):
    # override fields for EconomicAgent model
    agent_type = forms.ModelChoiceField(
        queryset=AgentType.objects.filter(is_context=True),
        empty_label=None,
        widget=forms.Select(
        attrs={'class': 'chzn-select'}))

    is_context = None # projects are always context_agents, hide the field

    # fields for Project model
    joining_style = forms.ChoiceField()
    visibility = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        super(ProjectCreateForm, self).__init__(*args, **kwargs)
        self.fields["joining_style"].choices = [(js[0], js[1]) for js in JOINING_STYLE_CHOICES]
        self.fields["visibility"].choices = [(vi[0], vi[1]) for vi in VISIBILITY_CHOICES]

    def clean(self):
        #import pdb; pdb.set_trace()
        data = super(ProjectCreateForm, self).clean()
        url = data["url"]
        if not url[0:3] == "http":
          data["url"] = "http://" + url
        #if type_of_user == "collective":
            #if int(number_of_shares) < 2:
            #    msg = "Number of shares must be at least 2 for a collective."
            #    self.add_error('number_of_shares', msg)

    def _clean_fields(self):
        super(ProjectCreateForm, self)._clean_fields()
        for name, value in self.cleaned_data.items():
            self.cleaned_data[name] = bleach.clean(value)

    class Meta: #(AgentCreateForm.Meta):
        model = Project #EconomicAgent
        #removed address and is_context
        fields = ('name', 'nick', 'agent_type', 'description', 'url', 'email', 'joining_style', 'visibility', 'fobi_slug')
        #exclude = ('is_context',)


class WorkAgentCreateForm(AgentCreateForm):
    # override fields for EconomicAgent model
    agent_type = forms.ModelChoiceField(
        queryset=AgentType.objects.all(), #filter(is_context=True),
        empty_label=None,
        widget=forms.Select(
        attrs={'class': 'chzn-select'}))

    is_context = None # projects are always context_agents, hide the field
    nick = None
    # fields for Project model
    #joining_style = forms.ChoiceField()
    #visibility = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        super(WorkAgentCreateForm, self).__init__(*args, **kwargs)
        #self.fields["joining_style"].choices = [(js[0], js[1]) for js in JOINING_STYLE_CHOICES]
        #self.fields["visibility"].choices = [(vi[0], vi[1]) for vi in VISIBILITY_CHOICES]


    class Meta: #(AgentCreateForm.Meta):
        model = EconomicAgent
        #removed address and is_context
        fields = ('name', 'agent_type', 'description', 'url', 'email', 'address', 'phone_primary',)
        #exclude = ('is_context',)


class WorkCasualTimeContributionForm(CasualTimeContributionForm):
    #resource_type = WorkModelChoiceField(
    #    queryset=EconomicResourceType.objects.all(),
    #    empty_label=None,
    #    widget=forms.Select(attrs={'class': 'chzn-select'}))
    context_agent = forms.ModelChoiceField(
        queryset=EconomicAgent.objects.open_projects(),
        label=_("Context"),
        empty_label=None,
        widget=forms.Select(attrs={'class': 'chzn-select'}))
    #event_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'class': 'item-date date-entry',}))
    #description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'item-description',}))
    #url = forms.URLField(required=False, widget=forms.TextInput(attrs={'class': 'url',}))
    #quantity = forms.DecimalField(required=False,
    #    widget=DecimalDurationWidget,
    #    help_text="hrs, mins")

    class Meta:
        model = EconomicEvent
        fields = ('event_date', 'resource_type', 'context_agent', 'quantity', 'is_contribution', 'url', 'description')

    def __init__(self, *args, **kwargs):
        super(WorkCasualTimeContributionForm, self).__init__(*args, **kwargs)
        #pattern = None
        #try:
        #    pattern = PatternUseCase.objects.get(use_case__identifier='non_prod').pattern
        #except PatternUseCase.DoesNotExist:
        #    pass
        #if pattern:
        #    self.fields["resource_type"].queryset = pattern.work_resource_types().order_by("name")

# public join form
class JoinRequestForm(forms.ModelForm):
    captcha = CaptchaField()

    project = None
    '''forms.ModelChoiceField(
        queryset=Project.objects.filter(joining_style='moderated', visibility='public'),
        empty_label=None,
        widget=forms.Select(
        attrs={'class': 'chzn-select'}))'''

    class Meta:
        model = JoinRequest
        exclude = ('agent', 'project', 'fobi_data',)

    def clean(self):
        #import pdb; pdb.set_trace()
        data = super(JoinRequestForm, self).clean()
        type_of_user = data["type_of_user"]
        #number_of_shares = data["number_of_shares"]
        #if type_of_user == "collective":
            #if int(number_of_shares) < 2:
            #    msg = "Number of shares must be at least 2 for a collective."
            #    self.add_error('number_of_shares', msg)

    def _clean_fields(self):
        super(JoinRequestForm, self)._clean_fields()
        for name, value in self.cleaned_data.items():
            self.cleaned_data[name] = bleach.clean(value)


class JoinRequestInternalForm(forms.ModelForm):
    captcha = None #CaptchaField()

    project = None
    '''forms.ModelChoiceField(
        queryset=Project.objects.filter(joining_style='moderated', visibility='public'),
        empty_label=None,
        widget=forms.Select(
        attrs={'class': 'chzn-select'}))'''

    class Meta:
        model = JoinRequest
        exclude = ('agent', 'project', 'fobi_data', 'type_of_user', 'name', 'surname', 'requested_username', 'email_address', 'phone_number', 'address',)

    def clean(self):
        #import pdb; pdb.set_trace()
        data = super(JoinRequestInternalForm, self).clean()
        #type_of_user = data["type_of_user"]
        #number_of_shares = data["number_of_shares"]
        #if type_of_user == "collective":
            #if int(number_of_shares) < 2:
            #    msg = "Number of shares must be at least 2 for a collective."
            #    self.add_error('number_of_shares', msg)

    def _clean_fields(self):
        super(JoinRequestInternalForm, self)._clean_fields()
        for name, value in self.cleaned_data.items():
            self.cleaned_data[name] = bleach.clean(value)



class JoinAgentSelectionForm(forms.Form):
    created_agent = AgentModelChoiceField(
        queryset=EconomicAgent.objects.without_join_request(),
        required=False)

