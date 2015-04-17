import sys
import datetime
from decimal import *
from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from valuenetwork.valueaccounting.models import *

class EquipmentUseForm(forms.ModelForm):
    event_date = forms.DateField(
        required=True, 
        label="Date of use",
        widget=forms.TextInput(attrs={'class': 'input-small date-entry', }))
    from_agent = forms.ModelChoiceField(
        required=True,
        queryset=EconomicAgent.objects.all(),
        label="Who is using",
        empty_label=None,
        widget=forms.Select(
            attrs={'class': 'chzn-select'})) 
    quantity = forms.DecimalField(required=True,
        label="Number of hours used",
        widget=forms.TextInput(attrs={'value': '1.00', 'class': 'quantity  input-mini'}))
        
    class Meta:
        model = EconomicEvent
        fields = ('from_agent', 'event_date', 'quantity')

    def __init__(self, resource=None, context_agent=None, *args, **kwargs):
        super(EquipmentUseForm, self).__init__(*args, **kwargs)
        #import pdb; pdb.set_trace()
        if context_agent:
            if resource:
                self.fields["from_agent"].queryset = resource.equipment_users(context_agent=context_agent)
            #self.fields["orders"].queryset = context_agent.orders_queryset()

class ConsumableForm(forms.Form):
    resource_id = forms.CharField(widget=forms.HiddenInput)
    quantity = forms.DecimalField(required=False,
        widget=forms.TextInput(attrs={'value': '0.00', 'class': 'quantity input-mini'}))
