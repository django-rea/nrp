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
        label="Equipment hours used",
        widget=forms.TextInput(attrs={'value': '1.00', 'class': 'quantity  input-mini'}))
    technician = forms.ModelChoiceField(
        required=False,
        queryset=EconomicAgent.objects.all(),
        label="Technician (if applicable)",
        widget=forms.Select(
            attrs={'class': 'chzn-select'}))
    technician_hours = forms.DecimalField(required=True,
        label="Technician hours spent",
        widget=forms.TextInput(attrs={'value': '0.00', 'class': 'quantity  input-mini'}))
        
    class Meta:
        model = EconomicEvent
        fields = ('from_agent', 'event_date', 'quantity')

    def __init__(self, use_resource=None, equip_resource=None, context_agent=None, *args, **kwargs):
        super(EquipmentUseForm, self).__init__(*args, **kwargs)
        #import pdb; pdb.set_trace()
        if context_agent:
            if use_resource:
                self.fields["from_agent"].queryset = use_resource.equipment_users(context_agent=context_agent)
        if equip_resource:
            self.fields["technician"].queryset = equip_resource.all_related_agents()

class ConsumableForm(forms.Form):
    resource_id = forms.CharField(widget=forms.HiddenInput)
    quantity = forms.DecimalField(required=False,
        widget=forms.TextInput(attrs={'value': '0.00', 'class': 'quantity input-mini'}))

class PaymentForm(forms.Form):
    resource_id = forms.CharField(widget=forms.HiddenInput)
    #event_reference = forms.CharField(
    #    required=True, 
    #    label="Paid by (cash, check, paypal, etc.)",
    #    widget=forms.TextInput(attrs={'class': 'reference',}))
