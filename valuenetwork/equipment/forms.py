import sys
import datetime
from decimal import *
from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from valuenetwork.valueaccounting.models import *
from valuenetwork.valueaccounting.forms import WorkModelChoiceField

 
class ProcessModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return ": ".join([obj.context_agent.nick, obj.shorter_label()])
    
class EquipmentUseForm(forms.ModelForm):
    event_date = forms.DateField(
        required=True, 
        label="Date of use",
        widget=forms.TextInput(attrs={'class': 'form-control input-sm date-entry', }))
    from_agent = forms.ModelChoiceField(
        required=True,
        queryset=EconomicAgent.objects.all(),
        label="Who is paying",
        empty_label=None,
        widget=forms.Select(
            attrs={'class': 'chzn-select form-control'})) 
    quantity = forms.DecimalField(required=True,
        label="Equipment hours used",
        widget=forms.TextInput(attrs={'value': '1.00', 'class': 'quantity input-sm form-control'}))
    technician = forms.ModelChoiceField(
        required=False,
        queryset=EconomicAgent.objects.all(),
        label="Technician (if applicable)",
        widget=forms.Select(
            attrs={'class': 'chzn-select form-control'}))
    technician_hours = forms.DecimalField(required=True,
        label="Technician hours spent",
        widget=forms.TextInput(attrs={'value': '0.00', 'class': 'quantity input-sm form-control'}))
        
    class Meta:
        model = EconomicEvent
        fields = ('from_agent', 'event_date', 'quantity')

    def __init__(self, equip_resource=None, context_agent=None,tech_type=None, *args, **kwargs):
        super(EquipmentUseForm, self).__init__(*args, **kwargs)
        #import pdb; pdb.set_trace()    
        #self.fields["process"].queryset = Process.objects.current()
        if equip_resource:
            self.fields["technician"].queryset = equip_resource.related_agents(role=tech_type)
            if context_agent:
                self.fields["from_agent"].queryset = equip_resource.equipment_users(context_agent=context_agent)

class ConsumableForm(forms.Form):
    resource_id = forms.CharField(widget=forms.HiddenInput)
    quantity = forms.DecimalField(required=False,
        widget=forms.TextInput(attrs={'value': '0.00', 'class': 'quantity input-sm form-control inline'}))

class PaymentForm(forms.Form):
    #resource_id = forms.CharField(widget=forms.HiddenInput)
    payment_method = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control input-sm pay'})) 
                                       
    def __init__(self, *args, **kwargs):
        super(PaymentForm, self).__init__(*args, **kwargs)
        self.fields["payment_method"].choices = [('Cash', 'Cash'), ('Check', 'Check'), ('Paypal', 'Paypal'), ('Other', 'Other')]                                      
    
class ProcessForm(forms.Form):                    
    process = ProcessModelChoiceField(
        required=False,
        queryset=Process.objects.current_or_future_with_use(),
        label="What project process will this be used in?", 
        widget=forms.Select(
            attrs={'class': 'chzn-select form-control'}))

class AdditionalCitationForm(forms.ModelForm):
    resource = forms.ModelChoiceField(
        queryset=EconomicResource.objects.all(), 
        label="Design to cite",
        empty_label=None,
        widget=forms.Select(attrs={'class': 'chzn-select form-control',}))
    quantity = forms.DecimalField(required=False,
        label="Allocate to this citation",
        widget=forms.TextInput(attrs={'value': '0.00', 'class': 'quantity form-control input-sm inline'}))
    
    class Meta:
        model = EconomicEvent
        fields = ('resource', 'quantity')
   
    def __init__(self, cite_rt=None, *args, **kwargs):
        super(AdditionalCitationForm, self).__init__(*args, **kwargs)
        if cite_rt:
            self.fields["resource"].queryset = EconomicResource.objects.filter(resource_type=cite_rt)  
            
class AdditionalWorkForm(forms.ModelForm):
    resource_type = WorkModelChoiceField(
        queryset=EconomicResourceType.objects.filter(behavior="work"), 
        label="Type of work",
        empty_label=None,
        widget=forms.Select(
            attrs={'class': 'chzn-select form-control'}))
    from_agent = forms.ModelChoiceField(
        required=False,
        queryset=EconomicAgent.objects.individuals(),
        label="Who worked",
        empty_label=None,
        widget=forms.Select(
            attrs={'class': 'chzn-select form-control'})) 
    quantity = forms.DecimalField(required=False,
        label="Hours worked",
        widget=forms.TextInput(attrs={'value': '0.00', 'class': 'form-control quantity input-sm'}))
    
    class Meta:
        model = EconomicEvent
        fields = ('resource_type', 'from_agent', 'quantity')
        