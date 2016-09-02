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
from valuenetwork.valueaccounting.forms import WorkModelChoiceField
from valuenetwork.valueaccounting.forms import AgentCreateForm

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


    class Meta: #(AgentCreateForm.Meta):
        model = Project #EconomicAgent
        #removed address and is_context
        fields = ('name', 'nick', 'agent_type', 'description', 'url', 'email', 'joining_style', 'visibility',)
        #exclude = ('is_context',)
