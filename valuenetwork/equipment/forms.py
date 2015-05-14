import sys
import datetime
from decimal import *
from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from valuenetwork.valueaccounting.models import *

 
class ProcessModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return ": ".join([obj.context_agent.nick, obj.shorter_label()])
    
class EquipmentUseForm(forms.ModelForm):
    event_date = forms.DateField(
        required=True, 
        label="Date of use",
        widget=forms.TextInput(attrs={'class': 'input-small date-entry', }))
    from_agent = forms.ModelChoiceField(
        required=True,
        queryset=EconomicAgent.objects.all(),
        label="Who is paying",
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

    def __init__(self, equip_resource=None, context_agent=None, *args, **kwargs):
        super(EquipmentUseForm, self).__init__(*args, **kwargs)
        #import pdb; pdb.set_trace()    
        #self.fields["process"].queryset = Process.objects.current()
        if equip_resource:
            self.fields["technician"].queryset = equip_resource.all_related_agents()
            if context_agent:
                self.fields["from_agent"].queryset = equip_resource.equipment_users(context_agent=context_agent)

class ConsumableForm(forms.Form):
    resource_id = forms.CharField(widget=forms.HiddenInput)
    quantity = forms.DecimalField(required=False,
        widget=forms.TextInput(attrs={'value': '0.00', 'class': 'quantity input-mini'}))

class PaymentForm(forms.Form):
    #resource_id = forms.CharField(widget=forms.HiddenInput)
    payment_method = forms.ChoiceField(widget=forms.Select(attrs={'class': 'input-small pay'})) 
                                       
    def __init__(self, *args, **kwargs):
        super(PaymentForm, self).__init__(*args, **kwargs)
        self.fields["payment_method"].choices = [('Cash', 'Cash'), ('Check', 'Check'), ('Paypal', 'Paypal'), ('Other', 'Other')]                                      
    
class ProcessForm(forms.Form):                    
    process = ProcessModelChoiceField(
        required=False,
        queryset=Process.objects.current_or_future(),
        label="What project process will this be used in?", 
        widget=forms.Select(
            attrs={'class': 'chzn-select'}))
   

    
    #commitment = forms.ModelChoiceField(
    #    required=False,
    #    queryset=Commitment.objects.all(),
    #    label="Is this printer use planned? If so, choose the plan",
    #    widget=forms.Select(
    #        attrs={'class': 'chzn-select'}))
    #event_reference = forms.CharField(
    #    required=True, 
    #    label="Paid by (cash, check, paypal, etc.)",
    #    widget=forms.TextInput(attrs={'class': 'reference',}))
