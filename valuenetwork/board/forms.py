import sys
import datetime
from decimal import *
from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from valuenetwork.valueaccounting.models import *

            
class ExchangeFlowForm(forms.Form):
    start_date = forms.DateField(required=True, 
        label=_("Transfer Date"),
        widget=forms.TextInput(attrs={'class': 'item-date date-entry',}))
    to_agent = forms.ModelChoiceField(required=False,
        queryset=EconomicAgent.objects.all(),
        label="Transferred To", 
        widget=forms.Select(
            attrs={'class': 'chzn-select'}))
    quantity = forms.DecimalField(required=True,
        label="Quantity",
        widget=forms.TextInput(attrs={'value': '1', 'class': 'quantity  input-small'}))
    paid = forms.DecimalField(required=True,
        label="Paid",
        widget=forms.TextInput(attrs={'value': '1', 'class': 'quantity  input-small'}))
    notes = forms.CharField(required=False,
        widget=forms.Textarea(attrs={'class': 'item-description',}))
    zero_out = forms.BooleanField(
        required=False,
        label="Last harvest of this resource type on this farm (zero out farm inventory)", 
        widget=forms.CheckboxInput())

class PlanProcessForm(forms.ModelForm):
    name = forms.CharField(widget=forms.TextInput(attrs={'class': 'input-xlarge',}))
    start_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))
    end_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))
    
    class Meta:
        model = Process
        fields = ('name', 'start_date', 'end_date')
        
class AvailableForm(forms.ModelForm):
    event_date = forms.DateField(
        required=True, 
        label="Available on",
        widget=forms.TextInput(attrs={'class': 'input-small date-entry', }))
    from_agent = forms.ModelChoiceField(
        required=True,
        label="Farm", 
        queryset=EconomicAgent.objects.all(),
        widget=forms.Select(
            attrs={'class': 'chzn-select'}))
    resource_type = forms.ModelChoiceField(
        queryset=EconomicResourceType.objects.all(),
        widget=forms.Select(
            attrs={'class': 'resource-type-selector resourceType chzn-select input-large'}))
    quantity = forms.DecimalField(required=True,
        label="Approximate quantity in pounds",
        widget=forms.TextInput(attrs={'value': '1', 'class': 'quantity  input-small'}))
    description = forms.CharField(
        required=False,
        label="Notes", 
        widget=forms.Textarea(attrs={'class': 'item-description',}))
        
    class Meta:
        model = EconomicEvent
        fields = ('from_agent', 'resource_type', 'event_date', 'quantity', 'description')

    def __init__(self, pattern=None, *args, **kwargs):
        super(AvailableForm, self).__init__(*args, **kwargs)
        #import pdb; pdb.set_trace()
        if pattern:
            self.pattern = pattern
            et = EventType.objects.get(name="Make Available")
            self.fields["resource_type"].queryset = pattern.get_resource_types(event_type=et)
 
