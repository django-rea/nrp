import sys
from decimal import *
from django import forms
from django.utils.translation import ugettext_lazy as _

from valuenetwork.tekextensions.widgets import SelectWithPopUp

from valuenetwork.valueaccounting.models import *

from valuenetwork.valueaccounting.widgets import DurationWidget, DecimalDurationWidget


class EconomicResourceForm(forms.ModelForm):
    url = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'input-xxlarge',}))
    photo_url = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'input-xxlarge',}))
    quantity = forms.DecimalField(widget=forms.TextInput(attrs={'class': 'input-small',}))
    quality = forms.DecimalField(required=False, widget=forms.TextInput(attrs={'class': 'input-small',}))

    class Meta:
        model = EconomicResource
        exclude = ('resource_type', 'author', 'owner', 'custodian', 'photo')


class FailedOutputForm(forms.ModelForm):
    quantity = forms.DecimalField(required=False, widget=forms.TextInput(attrs={'class': 'failed-quantity input-small',}))
    description = forms.CharField(
        label="Why failed",
        required=False, 
        widget=forms.Textarea(attrs={'class': 'item-description',}))

    class Meta:
        model = EconomicEvent
        fields = ('quantity', 'description')

class DemandSelectionForm(forms.Form):
    demand = forms.ModelChoiceField(
        queryset=Order.objects.all(), 
        label="For customer order or R&D project (optional)",
        required=False)


class OrderForm(forms.ModelForm):
    due_date = forms.CharField(widget=forms.TextInput(attrs={'class': 'input-small',}))

    class Meta:
        model = Order
        exclude = ('order_date', 'order_type')

class RandOrderForm(forms.ModelForm):
    receiver = forms.ModelChoiceField(
        queryset=EconomicAgent.objects.exclude(agent_type__member_type='inactive'), 
        required=False)
    provider = forms.ModelChoiceField(
        queryset=EconomicAgent.objects.exclude(agent_type__member_type='inactive'), 
        required=False)

    class Meta:
        model = Order
        fields = ('receiver', 'provider')


class ProcessForm(forms.ModelForm):
    start_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))
    end_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))

    class Meta:
        model = Process
        fields = ('name', 'project', 'url', 'start_date', 'end_date', 'notes' )


class ProcessInputForm(forms.ModelForm):
    resource_type = forms.ModelChoiceField(
        queryset=EconomicResourceType.objects.process_inputs(), 
        widget=SelectWithPopUp(
            model=EconomicResourceType,
            attrs={'class': 'resource-type-selector'}))
    quantity = forms.DecimalField(required=False,
        widget=forms.TextInput(attrs={'value': '0.0', 'class': 'quantity input-small'}))
    unit_of_quantity = forms.ModelChoiceField(
        queryset=Unit.objects.exclude(unit_type='value'), 
        empty_label=None,
        widget=forms.Select(attrs={'class': 'input-medium',}))
    description = forms.CharField(
        required=False, 
        widget=forms.Textarea(attrs={'class': 'item-description',}))

    class Meta:
        model = Commitment
        fields = ('resource_type', 'quantity', 'unit_of_quantity', 'description')


class ProcessOutputForm(forms.ModelForm):
    resource_type = forms.ModelChoiceField(
        queryset=EconomicResourceType.objects.process_outputs(), 
        widget=SelectWithPopUp(
            model=EconomicResourceType,
            attrs={'class': 'resource-type-selector'}))
    quantity = forms.DecimalField(required=False,
        widget=forms.TextInput(attrs={'value': '0.0', 'class': 'quantity  input-small'}))
    unit_of_quantity = forms.ModelChoiceField(
        queryset=Unit.objects.exclude(unit_type='value').exclude(unit_type='time'), 
        empty_label=None,
        widget=forms.Select(attrs={'class': 'input-medium',}))
    description = forms.CharField(
        required=False, 
        widget=forms.Textarea(attrs={'class': 'item-description',}))

    class Meta:
        model = Commitment
        fields = ('resource_type', 'quantity', 'unit_of_quantity', 'description')


class CommitmentForm(forms.ModelForm):
    start_date = forms.DateField(widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))
    quantity = forms.DecimalField(required=False, widget=forms.TextInput(attrs={'class': 'quantity input-small',}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'item-description',}))

    class Meta:
        model = Commitment
        fields = ('start_date', 'quantity', 'unit_of_quantity', 'description')


class WorkbookForm(forms.ModelForm):
    #event_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'item-description',}))
    quantity = forms.DecimalField(required=False,
        widget=DecimalDurationWidget,
        help_text="days, hours, minutes")
	
    class Meta:
        model = EconomicEvent
        fields = ('quantity', 'description')


class CasualTimeContributionForm(forms.ModelForm):
    event_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'item-description',}))
    quantity = forms.DecimalField(required=False,
        widget=DecimalDurationWidget,
        help_text="days, hours, minutes")
	
    class Meta:
        model = EconomicEvent
        fields = ('event_date', 'resource_type', 'project', 'quantity', 'description')

    def __init__(self, *args, **kwargs):
        super(CasualTimeContributionForm, self).__init__(*args, **kwargs)
        self.fields["resource_type"].choices = [(rt.id, rt.name) for rt in EconomicResourceType.objects.types_of_work()]
        self.fields["project"].choices = [(p.id, p.name) for p in Project.objects.all()]


class OrderItemForm(forms.ModelForm):
    resource_type_id = forms.CharField(widget=forms.HiddenInput)
    quantity = forms.DecimalField(required=False, widget=forms.TextInput(attrs={'class': 'input-small',}))
    url = forms.URLField(required=False, widget=forms.TextInput(attrs={'class': 'url',}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'item-description',}))

    def __init__(self, resource_type, *args, **kwargs):
        super(OrderItemForm, self).__init__(*args, **kwargs)
        self.resource_type = resource_type

    class Meta:
        model = Commitment
        fields = ('quantity', 'description')


class OrderItemOptionsForm(forms.Form):

    options = forms.ChoiceField()

    def __init__(self, feature, *args, **kwargs):
        super(OrderItemOptionsForm, self).__init__(*args, **kwargs)
        self.feature = feature
        self.fields["options"].choices = [(opt.id, opt.component.name) for opt in feature.options.all()]


class OptionsForm(forms.Form):

    options = forms.CharField(
        label=_("Options"),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
    )

    def __init__(self, feature, *args, **kwargs):
        super(OptionsForm, self).__init__(*args, **kwargs)
        if feature.option_category:
            options = EconomicResourceType.objects.filter(category=feature.option_category)
        else:
            options = EconomicResourceType.objects.all()
        self.fields["options"].choices = [(rt.id, rt.name) for rt in options]

class EconomicResourceTypeForm(forms.ModelForm):
    
    class Meta:
        model = EconomicResourceType
        exclude = ('parent', 'created_by', 'changed_by')


class EconomicResourceTypeWithPopupForm(forms.ModelForm):
    unit = forms.ModelChoiceField(
        queryset=Unit.objects.all(),  
        widget=SelectWithPopUp(model=Unit))

    class Meta:
        model = EconomicResourceType
        exclude = ('parent',)

    @classmethod
    def is_multipart(cls):
        return True


class AgentResourceTypeForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(AgentResourceTypeForm, self).__init__(*args, **kwargs)
        self.fields["agent"].choices = [
            (agt.id, agt.name) for agt in EconomicAgent.objects.all()
        ]


    class Meta:
        model = AgentResourceType
        exclude = ('resource_type', 'relationship')


class XbillProcessTypeForm(forms.ModelForm):
    quantity = forms.DecimalField(max_digits=8, decimal_places=2)
    estimated_duration = forms.IntegerField(required=False,
        widget=DurationWidget,
        help_text="days, hours, minutes")

    class Meta:
        model = ProcessType
        exclude = ('parent',)


class ChangeProcessTypeForm(forms.ModelForm):
    estimated_duration = forms.IntegerField(required=False,
        widget=DurationWidget,
        help_text="days, hours, minutes")

    class Meta:
        model = ProcessType
        exclude = ('parent',)

class FeatureForm(forms.ModelForm):

    class Meta:
        model = Feature
        exclude = ('product', 'process_type')


class ProcessTypeResourceTypeForm(forms.ModelForm):
    resource_type = forms.ModelChoiceField(
        queryset=EconomicResourceType.objects.all(), 
        empty_label=None, 
        widget=SelectWithPopUp(
            model=EconomicResourceType,
            attrs={'class': 'resource-type-selector'}))
    quantity = forms.DecimalField(required=False,
        widget=forms.TextInput(attrs={'value': '0.0', 'class': 'quantity'}))
    unit_of_quantity = forms.ModelChoiceField(
        required = False,
        queryset=Unit.objects.all(),  
        widget=SelectWithPopUp(model=Unit))

    class Meta:
        model = ProcessTypeResourceType
        exclude = ('process_type', 'relationship')


class LaborInputForm(forms.ModelForm):
    resource_type = forms.ModelChoiceField(
        queryset=EconomicResourceType.objects.types_of_work(), 
        empty_label=None, 
        widget=SelectWithPopUp(
            model=EconomicResourceType,
            attrs={'class': 'resource-type-selector'}))
    relationship = forms.ModelChoiceField(
        queryset=ResourceRelationship.objects.exclude(direction='out'), 
        empty_label=None, 
        widget=SelectWithPopUp(model=ResourceRelationship))
    quantity = forms.DecimalField(required=False,
        widget=forms.TextInput(attrs={'value': '0.0', 'class': 'quantity'}))
    unit_of_quantity = forms.ModelChoiceField(
        queryset=Unit.objects.filter(unit_type='time'),  
        widget=SelectWithPopUp(model=Unit))

    class Meta:
        model = ProcessTypeResourceType
        exclude = ('process_type',)


class TimeForm(forms.Form):

    description = forms.CharField(
        label=_("Description"),
        required=False,
        widget=forms.Textarea(attrs={"cols": "80"}),
    )
    url = forms.CharField(
        label=_("URL"),
        max_length=96,
        required=False,
        widget=forms.TextInput(attrs={"size": "80"}),
    )

class EquationForm(forms.Form):

    equation = forms.CharField(
        label=_("Equation"),
        required=True,
        widget=forms.Textarea(attrs={"rows": "4", "cols": "60"}),
    )

    amount = forms.CharField(
        label=_("Amount to distribute"),
        required=False,
        widget=forms.TextInput(),
    )


    def clean_equation(self):
        equation = self.cleaned_data["equation"]
        safe_dict = {}
        safe_dict['hours'] = 1
        safe_dict['rate'] = 1
        safe_dict['importance'] = 1
        safe_dict['reputation'] = 1
        safe_dict['seniority'] = 1

        try:
            eval(equation, {"__builtins__":None}, safe_dict)
        except NameError:
            raise forms.ValidationError(sys.exc_info()[1])
        except SyntaxError:
            raise forms.ValidationError("Equation syntax error")
        except:
            raise forms.ValidationError(sys.exc_info()[0])

        return equation
