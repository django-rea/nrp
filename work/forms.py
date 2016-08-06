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

class UploadAgentForm(forms.ModelForm):
    photo_url = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'url input-xxlarge',}))
    
    class Meta:
        model = EconomicAgent
        fields = ('photo', 'photo_url')


class MembershipRequestForm(forms.ModelForm):
    captcha = CaptchaField()

    class Meta:
        model = MembershipRequest
        exclude = ('agent',)

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
        queryset=EconomicAgent.objects.individuals(),
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
        self.fields["context_agent"].choices = [(ct.id, ct) for ct in contexts]
        peeps = [agent,]
        from_agent_choices = [('', 'Unassigned'), (agent.id, agent),]
        for context in contexts:
            associations = agent.is_associate_of.filter(has_associate=context)
            if associations:
                association = associations[0]
                if association.association_type.association_behavior == "manager":
                    peeps.extend(context.task_assignment_candidates())
        if len(peeps) > 1:
            peeps = list(OrderedDict.fromkeys(peeps))
        from_agent_choices = [('', 'Unassigned')] + [(peep.id, peep) for peep in peeps]
        
        self.fields["from_agent"].choices = from_agent_choices
        if pattern:
            self.pattern = pattern
            self.fields["resource_type"].choices = [(rt.id, rt) for rt in pattern.todo_resource_types()]

