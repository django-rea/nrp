import sys
import datetime
from decimal import *
from django import forms
from django.utils.translation import ugettext_lazy as _

from valuenetwork.tekextensions.widgets import SelectWithPopUp

from valuenetwork.valueaccounting.models import *

from valuenetwork.valueaccounting.widgets import DurationWidget, DecimalDurationWidget


class AgentForm(forms.ModelForm):
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'input-xlarge',}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'input-xlarge',}))
    email = forms.EmailField(widget=forms.TextInput(attrs={'class': 'input-xxlarge',}))
    address = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'input-xxlarge',}))
    url = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'url input-xxlarge',}))
    description = forms.CharField(
        required=False, 
        widget=forms.Textarea(attrs={'class': 'input-xxlarge',}))
    agent_type = forms.ModelChoiceField(
        queryset=AgentType.objects.all(),
        empty_label=None,
        widget=forms.Select(
            attrs={'class': 'chzn-select'}))

    class Meta:
        model = EconomicAgent
        fields = ('nick', 'agent_type', 'description', 'url', 'address', 'email')
        

class EconomicResourceForm(forms.ModelForm):
    url = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'url input-xxlarge',}))
    photo_url = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'url input-xxlarge',}))
    quantity = forms.DecimalField(widget=forms.TextInput(attrs={'class': 'quantity input-small',}))
    quality = forms.DecimalField(required=False, widget=forms.TextInput(attrs={'class': 'quality input-small',}))

    class Meta:
        model = EconomicResource
        exclude = ('resource_type', 'owner', 'custodian', 'photo')


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
        queryset=Order.objects.exclude(order_type="holder"), 
        label="For customer or R&D order (optional)",
        required=False)

# does not appear to be used anywhere
class OutputResourceTypeSelectionForm(forms.Form):
    resource_type = forms.ModelChoiceField(
        queryset=EconomicResourceType.objects.all(), 
        label="Output Resource Type", 
        widget=SelectWithPopUp(
            model=EconomicResourceType,
            attrs={'class': 'resource-type-selector'}))


class OrderForm(forms.ModelForm):
    due_date = forms.CharField(widget=forms.TextInput(attrs={'class': 'input-small',}))

    class Meta:
        model = Order
        exclude = ('order_date', 'order_type')

class RandOrderForm(forms.ModelForm):
    receiver = forms.ModelChoiceField(
        queryset=EconomicAgent.objects.exclude(agent_type__member_type='inactive'),
        label="Receiver (optional)", 
        required=False)
    provider = forms.ModelChoiceField(
        queryset=EconomicAgent.objects.exclude(agent_type__member_type='inactive'), 
        label="Provider (optional)", 
        required=False)
    create_order = forms.BooleanField(
        label="R&D Order without receiver",
        required=False, 
        widget=forms.CheckboxInput())

    class Meta:
        model = Order
        fields = ('receiver', 'provider')


class ProcessForm(forms.ModelForm):
    name = forms.CharField(widget=forms.TextInput(attrs={'class': 'input-xlarge',}))
    process_pattern = forms.ModelChoiceField(
        queryset=ProcessPattern.objects.production_patterns(),
        empty_label=None)
    start_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))
    end_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))

    class Meta:
        model = Process
        fields = ('name', 'project', 'process_pattern', 'start_date', 'end_date', 'notes' )


class NamelessProcessForm(forms.ModelForm):
    start_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))
    end_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))

    class Meta:
        model = Process
        fields = ('project', 'start_date', 'end_date', 'notes' )


#used in labnotes, create, copy and change_process, and create and change_rand
class ProcessInputForm(forms.ModelForm):
    resource_type = forms.ModelChoiceField(
        queryset=EconomicResourceType.objects.all(), 
        widget=forms.Select(
            attrs={'class': 'resource-type-selector chzn-select input-xlarge'}))
        #widget=SelectWithPopUp(
        #    model=EconomicResourceType,
        #    attrs={'class': 'resource-type-selector chzn-select input-xlarge'}))
    quantity = forms.DecimalField(required=False,
        widget=forms.TextInput(attrs={'value': '1.0', 'class': 'quantity input-small'}))
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

    def __init__(self, pattern=None, *args, **kwargs):
        super(ProcessInputForm, self).__init__(*args, **kwargs)
        use_pattern = True
        if self.instance:
            if self.instance.id:
                use_pattern = False
                ct = Commitment.objects.get(id=self.instance.id)
                rt = ct.resource_type
                self.fields["resource_type"].queryset = EconomicResourceType.objects.filter(id=rt.id)
        if pattern:
            if use_pattern:
                self.pattern = pattern
                self.fields["resource_type"].queryset = pattern.input_resource_types()


#used in labnotes, create, copy and change_process, and create and change_rand
class ProcessOutputForm(forms.ModelForm):
    resource_type = forms.ModelChoiceField(
        queryset=EconomicResourceType.objects.all(), 
        widget=forms.Select(
            attrs={'class': 'resource-type-selector chzn-select input-xlarge'}))
        #widget=SelectWithPopUp(
        #    model=EconomicResourceType,
        #    attrs={'class': 'resource-type-selector chzn-select input-xlarge'}))
    quantity = forms.DecimalField(required=False,
        widget=forms.TextInput(attrs={'value': '1.0', 'class': 'quantity  input-small'}))
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

    def __init__(self, pattern=None, *args, **kwargs):
        super(ProcessOutputForm, self).__init__(*args, **kwargs)
        #import pdb; pdb.set_trace()
        use_pattern = True
        if self.instance:
            if self.instance.id:
                use_pattern = False
                ct = Commitment.objects.get(id=self.instance.id)
                rt = ct.resource_type
                self.fields["resource_type"].queryset = EconomicResourceType.objects.filter(id=rt.id)
        if pattern:
            if use_pattern:
                self.pattern = pattern
                self.fields["resource_type"].queryset = pattern.output_resource_types()


class WorkModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name


class TodoForm(forms.ModelForm):
    from_agent = forms.ModelChoiceField(
        required=False,
        queryset=EconomicAgent.objects.filter(agent_type__member_type='agent'),
        label="Assigned to",  
        widget=forms.Select(
            attrs={'class': 'chzn-select'}))
    resource_type = WorkModelChoiceField(
        queryset=EconomicResourceType.objects.all(), 
        label="Type of work", 
        empty_label=None,
        widget=forms.Select(
            attrs={'class': 'chzn-select'}))
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(), 
        empty_label=None,
        widget=forms.Select(
            attrs={'class': 'chzn-select'}))
    due_date = forms.DateField(widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))
    description = forms.CharField(
        required=False, 
        widget=forms.Textarea(attrs={'class': 'todo-description input-xlarge',}))
    url = forms.URLField(required=False, widget=forms.TextInput(attrs={'class': 'url input-xlarge',}))

    class Meta:
        model = Commitment
        fields = ('from_agent', 'project', 'resource_type', 'due_date', 'description', 'url')

    def __init__(self, pattern=None, *args, **kwargs):
        super(TodoForm, self).__init__(*args, **kwargs)
        if pattern:
            self.pattern = pattern
            self.fields["resource_type"].choices = [(rt.id, rt) for rt in pattern.todo_resource_types()]


class ProcessCitationForm(forms.Form):
    #todo: this could now become a ModelChoiceField
    resource_type = forms.ChoiceField( 
        widget=forms.Select(attrs={'class': 'chzn-select input-xlarge'}))
    description = forms.CharField(
        required=False, 
        widget=forms.Textarea(attrs={'class': 'item-description',}))

    def __init__(self, pattern=None, *args, **kwargs):
        super(ProcessCitationForm, self).__init__(*args, **kwargs)
        if pattern:
            self.pattern = pattern
            self.fields["resource_type"].choices = [('', '----------')] + [(rt.id, rt) for rt in pattern.citables_with_resources()]
        else:
            self.fields["resource_type"].choices = [('', '----------')] + [(rt.id, rt) for rt in EconomicResourceType.objects.all()]

        
class ProcessCitationCommitmentForm(forms.ModelForm):
    resource_type = forms.ModelChoiceField(
        queryset=EconomicResourceType.objects.all(),
        widget=forms.Select(attrs={'class': 'input-xlarge'}))
    quantity = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput())
    description = forms.CharField(
        required=False, 
        widget=forms.Textarea(attrs={'class': 'item-description',}))

    class Meta:
        model = Commitment
        fields = ('resource_type', 'description', 'quantity')

    def __init__(self, pattern=None, *args, **kwargs):
        super(ProcessCitationCommitmentForm, self).__init__(*args, **kwargs)
        use_pattern = True
        if self.instance:
            if self.instance.id:
                use_pattern = False
                ct = Commitment.objects.get(id=self.instance.id)
                rt = ct.resource_type
                self.fields["resource_type"].queryset = EconomicResourceType.objects.filter(id=rt.id)
        if pattern:
            if use_pattern:
                self.pattern = pattern
                self.fields["resource_type"].choices = [('', '----------')] + [(rt.id, rt) for rt in pattern.citables_with_resources()]


class SelectCitationResourceForm(forms.Form):
    resource_type = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'input-xlarge', 'onchange': 'getResources();'}))
    resource = forms.ChoiceField(widget=forms.Select(attrs={'class': 'input-xlarge'})) 

    def __init__(self, pattern, *args, **kwargs):
        super(SelectCitationResourceForm, self).__init__(*args, **kwargs)
        self.pattern = pattern
        self.fields["resource_type"].choices = [('', '----------')] + [(rt.id, rt) for rt in pattern.citables_with_resources()]
 
class CommitmentForm(forms.ModelForm):
    start_date = forms.DateField(widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))
    quantity = forms.DecimalField(required=False, widget=forms.TextInput(attrs={'class': 'quantity input-small',}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'item-description',}))

    class Meta:
        model = Commitment
        fields = ('start_date', 'quantity', 'unit_of_quantity', 'description')


class WorkbookForm(forms.ModelForm):
    work_done = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput())
    process_done = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput())
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'item-description',}))
    quantity = forms.DecimalField(required=False,
        widget=DecimalDurationWidget,
        help_text="hours, minutes")
	
    class Meta:
        model = EconomicEvent
        fields = ('quantity', 'description')


class PastWorkForm(forms.ModelForm):
    id = forms.CharField(required=False, widget=forms.HiddenInput)
    work_done = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput())
    process_done = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput())
    event_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'item-description',}))
    quantity = forms.DecimalField(required=False,
        widget=DecimalDurationWidget,
        help_text="hours, minutes")
	
    class Meta:
        model = EconomicEvent
        fields = ('id', 'event_date', 'quantity', 'description')

class SimpleOutputForm(forms.ModelForm):
    event_date = forms.DateField(
        label="Date created",
        initial=datetime.date.today,  
        widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))

    class Meta:
        model = EconomicEvent
        fields = ('project', 'event_date')

    def __init__(self, *args, **kwargs):
        super(SimpleOutputForm, self).__init__(*args, **kwargs)
        self.fields["project"].choices = [(p.id, p) for p in Project.objects.all()]


# used in log_simple()
class SimpleOutputResourceForm(forms.ModelForm):
    resource_type = forms.ModelChoiceField(
        queryset=EconomicResourceType.objects.all(),
        label="Type of resource created",
        empty_label=None,
        widget=forms.Select(
            attrs={'class': 'resource-type-selector chzn-select input-xlarge'}))
        #widget=SelectWithPopUp(
        #    model=EconomicResourceType,
        #    attrs={'class': 'resource-type-selector chzn-select'})) 
    identifier = forms.CharField(
        required=True, 
        label="Name",
        widget=forms.TextInput(attrs={'class': 'item-name',}))
    notes = forms.CharField(
        required=True,
        label="Notes", 
        widget=forms.Textarea(attrs={'class': 'item-description',}))
    url = forms.URLField(
        required=True, 
        label="URL",
        widget=forms.TextInput(attrs={'class': 'url',}))
    #Photo URL:

    class Meta:
        model = EconomicResource
        fields = ('resource_type','identifier', 'url', 'notes')

    def __init__(self, pattern, *args, **kwargs):
        super(SimpleOutputResourceForm, self).__init__(*args, **kwargs)
        self.pattern = pattern
        self.fields["resource_type"].choices = [(rt.id, rt) for rt in pattern.output_resource_types()]

class SimpleWorkForm(forms.ModelForm):
    resource_type = WorkModelChoiceField(
        queryset=EconomicResourceType.objects.all(),
        label="Type of work done",
        empty_label=None,
        widget=forms.Select(
            attrs={'class': 'chzn-select'})) 
    quantity = forms.DecimalField(required=True,
        widget=DecimalDurationWidget,
        label="Time spent",
        help_text="hours, minutes")
   
    class Meta:
        model = EconomicEvent
        fields = ('resource_type','quantity')

    def __init__(self, pattern=None, *args, **kwargs):
        #import pdb; pdb.set_trace()
        super(SimpleWorkForm, self).__init__(*args, **kwargs)
        if pattern:
            self.pattern = pattern
            self.fields["resource_type"].choices = [(rt.id, rt) for rt in pattern.work_resource_types()]


class WorkCommitmentForm(forms.ModelForm):
    resource_type = WorkModelChoiceField(
        queryset=EconomicResourceType.objects.all(),
        label="Type of work",
        empty_label=None,
        widget=forms.Select(
            attrs={'class': 'chzn-select'})) 
    quantity = forms.DecimalField(required=True,
        widget=DecimalDurationWidget,
        label="Estimated time",
        help_text="hours, minutes")
   
    class Meta:
        model = Commitment
        fields = ('resource_type','quantity')

    def __init__(self, pattern=None, *args, **kwargs):
        #import pdb; pdb.set_trace()
        super(WorkCommitmentForm, self).__init__(*args, **kwargs)
        if pattern:
            self.pattern = pattern
            self.fields["resource_type"].queryset = pattern.work_resource_types()


class ProcessWorkForm(forms.ModelForm):
    resource_type = WorkModelChoiceField(
        queryset=EconomicResourceType.objects.all(),
        label="Type of work",
        widget=forms.Select(
            attrs={'class': 'chzn-select'})) 
    quantity = forms.DecimalField(required=True,
        widget=DecimalDurationWidget,
        label="Estimated time",
        help_text="hours, minutes")
    description = forms.CharField(
        required=False, 
        widget=forms.Textarea(attrs={'class': 'item-description',}))
   
    class Meta:
        model = Commitment
        fields = ('resource_type','quantity', 'description')

    def __init__(self, pattern=None, *args, **kwargs):
        #import pdb; pdb.set_trace()
        super(ProcessWorkForm, self).__init__(*args, **kwargs)
        if pattern:
            self.pattern = pattern
            self.fields["resource_type"].queryset = pattern.work_resource_types()


class WorkEventChangeForm(forms.ModelForm):
    id = forms.CharField(required=False, widget=forms.HiddenInput)
    event_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))
    quantity = forms.DecimalField(required=False,
        widget=DecimalDurationWidget,
        help_text="hours, minutes")
	
    class Meta:
        model = EconomicEvent
        fields = ('id', 'event_date', 'quantity')


class WorkContributionChangeForm(forms.ModelForm):
    id = forms.CharField(required=False, widget=forms.HiddenInput)
    event_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))
    resource_type = WorkModelChoiceField(
        queryset=EconomicResourceType.objects.all(), 
        label="Type of work", 
        empty_label=None,
        widget=forms.Select(
            attrs={'class': 'chzn-select'}))
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(), 
        empty_label=None,
        widget=forms.Select(
            attrs={'class': 'chzn-select'}))
    quantity = forms.DecimalField(required=False,
        widget=DecimalDurationWidget,
        label = "Time spent",
        help_text="hours, minutes")
    url = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'url input-xxlarge',}))
    description = forms.CharField(
        required=False, 
        widget=forms.Textarea(attrs={'class': 'input-xxlarge',}))
	
    class Meta:
        model = EconomicEvent
        fields = ('id', 'event_date', 'resource_type', 'project', 'quantity', 'url', 'description')


class EventChangeDateForm(forms.ModelForm):
    id = forms.CharField(required=False, widget=forms.HiddenInput)
    event_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))
	
    class Meta:
        model = EconomicEvent
        fields = ('id', 'event_date')

class EventChangeQuantityForm(forms.ModelForm):
    id = forms.CharField(required=False, widget=forms.HiddenInput)
    quantity = forms.DecimalField(widget=forms.TextInput(attrs={'class': 'quantity input-small',}))
	
    class Meta:
        model = EconomicEvent
        fields = ('id', 'quantity')


class WorkSelectionForm(forms.Form):
    type_of_work = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        super(WorkSelectionForm, self).__init__(*args, **kwargs)
        self.fields["type_of_work"].choices = [('', '----------')] + [(rt.id, rt.name) for rt in EconomicResourceType.objects.all()]


class ProjectSelectionForm(forms.Form):
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        empty_label=None,
        widget=forms.Select(
            attrs={'class': 'chzn-select'}))


class PatternSelectionForm(forms.Form):
    pattern = forms.ModelChoiceField(
        queryset=ProcessPattern.objects.all(),
        widget=forms.Select(
            attrs={'class': 'chzn-select'}))

class PatternProdSelectionForm(forms.Form):
    pattern = forms.ModelChoiceField(
        queryset=ProcessPattern.objects.production_patterns(),
        empty_label=None,
        widget=forms.Select(
            attrs={'class': 'chzn-select'}))


class CasualTimeContributionForm(forms.ModelForm):
    resource_type = WorkModelChoiceField(
        queryset=EconomicResourceType.objects.all(), 
        empty_label=None, 
        widget=forms.Select(attrs={'class': 'chzn-select'}))
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(), 
        empty_label=None, 
        widget=forms.Select(attrs={'class': 'chzn-select'}))
    event_date = forms.DateField(required=False, widget=forms.TextInput(attrs={'class': 'item-date date-entry',}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'item-description',}))
    quantity = forms.DecimalField(required=False,
        widget=DecimalDurationWidget,
        help_text="hrs, mins")
	
    class Meta:
        model = EconomicEvent
        fields = ('event_date', 'resource_type', 'project', 'quantity', 'url', 'description')

    def __init__(self, *args, **kwargs):
        super(CasualTimeContributionForm, self).__init__(*args, **kwargs)
        pattern = None
        try:
            pattern = PatternUseCase.objects.get(use_case='non_prod').pattern
        except PatternUseCase.DoesNotExist:
            pass
        if pattern:
            self.fields["resource_type"].queryset = pattern.work_resource_types().order_by("name")


class DateSelectionForm(forms.Form):
    start_date = forms.DateField(widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))
    end_date = forms.DateField(widget=forms.TextInput(attrs={'class': 'input-small date-entry',}))


class ResourceTypeFacetValueForm(forms.Form):
    facet_id = forms.CharField(widget=forms.HiddenInput)
    value = forms.ChoiceField()


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
        exclude = ('parent', 'created_by', 'changed_by', 'category')


# used in EconomicResourceType.add_new_form(cls), which is used in popups
# does not matter if we disable popups
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


class EconomicResourceTypeFacetForm(forms.Form):
    #coding in process, probably doesn't work
    
    facet_value = forms.ChoiceField()

    def __init__(self, rt, facet, *args, **kwargs):
        super(EconomicResourceTypeFacetForm, self).__init__(*args, **kwargs)
        self.rt = rt
        self.facet = facet
        self.fields["facet_value"].choices = [('', '----------')] + [(fv.value, fv.value) for fv in facet.value_list()]


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
        exclude = ('product', 'relationship', 'process_type')


# used in create_process_type_input(), change_process_type_input(),
# ProcessType.xbill_input_form() and ProcessTypeResourceType.xbill_input_form()
# all of those are used in recipes
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
        exclude = ('process_type', 'relationship', 'event_type')


class ProcessTypeInputForm(forms.ModelForm):
    resource_type = forms.ModelChoiceField(
        queryset=EconomicResourceType.objects.all(),  
        widget=SelectWithPopUp(
            model=EconomicResourceType,
            attrs={'class': 'resource-type-selector input-xlarge' }))
    quantity = forms.DecimalField(required=False,
        widget=forms.TextInput(attrs={'value': '0.0', 'class': 'quantity'}))
    unit_of_quantity = forms.ModelChoiceField(
        required = False,
        queryset=Unit.objects.all(),  
        widget=SelectWithPopUp(model=Unit))

    class Meta:
        model = ProcessTypeResourceType
        exclude = ('process_type', 'relationship', 'event_type')

    def __init__(self, process_type=None, *args, **kwargs):
        super(ProcessTypeInputForm, self).__init__(*args, **kwargs)
        #import pdb; pdb.set_trace()
        use_pattern = True
        pattern = None
        if process_type:
            pattern = process_type.process_pattern
        if self.instance:
            if self.instance.id:
                use_pattern = False
                inst = ProcessTypeResourceType.objects.get(id=self.instance.id)
                rt = inst.resource_type
                self.fields["resource_type"].queryset = EconomicResourceType.objects.filter(id=rt.id)
        if pattern:
            if use_pattern:
                self.pattern = pattern
                output_ids = [pt.id for pt in process_type.produced_resource_types()]
                self.fields["resource_type"].queryset = pattern.input_resource_types().exclude(id__in=output_ids)


class CitableModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return ": ".join([obj.name, obj.facet_values_list()])

        
class ProcessTypeCitableForm(forms.ModelForm):
    resource_type = CitableModelChoiceField(
        queryset=EconomicResourceType.objects.all(), 
        widget=SelectWithPopUp(
            model=EconomicResourceType,
            attrs={'class': 'resource-type-selector input-xlarge' }))
    quantity = forms.DecimalField(required=False,
        widget=forms.TextInput(attrs={'value': '0.0', 'class': 'quantity'}))
    unit_of_quantity = forms.ModelChoiceField(
        required = False,
        queryset=Unit.objects.all(),  
        widget=SelectWithPopUp(model=Unit))

    class Meta:
        model = ProcessTypeResourceType
        exclude = ('process_type', 'relationship', 'event_type')

    def __init__(self, process_type=None, *args, **kwargs):
        super(ProcessTypeCitableForm, self).__init__(*args, **kwargs)
        #import pdb; pdb.set_trace()
        use_pattern = True
        pattern = None
        if process_type:
            pattern = process_type.process_pattern
        if self.instance:
            if self.instance.id:
                use_pattern = False
                inst = ProcessTypeResourceType.objects.get(id=self.instance.id)
                rt = inst.resource_type
                self.fields["resource_type"].queryset = EconomicResourceType.objects.filter(id=rt.id)
        if pattern:
            if use_pattern:
                self.pattern = pattern
                output_ids = [pt.id for pt in process_type.produced_resource_types()]
                self.fields["resource_type"].queryset = pattern.citable_resource_types().exclude(id__in=output_ids)


class ProcessTypeWorkForm(forms.ModelForm):
    resource_type = forms.ModelChoiceField(
        queryset=EconomicResourceType.objects.all(), 
        widget=SelectWithPopUp(
            model=EconomicResourceType,
            attrs={'class': 'resource-type-selector input-xlarge' }))
    quantity = forms.DecimalField(required=False,
        widget=forms.TextInput(attrs={'value': '0.0', 'class': 'quantity'}))
    unit_of_quantity = forms.ModelChoiceField(
        required = False,
        queryset=Unit.objects.all(),  
        widget=SelectWithPopUp(model=Unit))

    class Meta:
        model = ProcessTypeResourceType
        exclude = ('process_type', 'relationship', 'event_type')

    def __init__(self, process_type=None, *args, **kwargs):
        super(ProcessTypeWorkForm, self).__init__(*args, **kwargs)
        #import pdb; pdb.set_trace()
        use_pattern = True
        pattern = None
        if process_type:
            pattern = process_type.process_pattern
        if self.instance:
            if self.instance.id:
                use_pattern = False
                inst = ProcessTypeResourceType.objects.get(id=self.instance.id)
                rt = inst.resource_type
                self.fields["resource_type"].queryset = EconomicResourceType.objects.filter(id=rt.id)
        if pattern:
            if use_pattern:
                self.pattern = pattern
                self.fields["resource_type"].queryset = pattern.work_resource_types()


# used in ProcessTypeResourceType.xbill_change_form()
class LaborInputForm(forms.ModelForm):
    resource_type = forms.ModelChoiceField(
        queryset=EconomicResourceType.objects.all(), 
        empty_label=None, 
        widget=SelectWithPopUp(
            model=EconomicResourceType,
            attrs={'class': 'resource-type-selector'}))
    quantity = forms.DecimalField(required=False,
        widget=forms.TextInput(attrs={'value': '0.0', 'class': 'quantity'}))
    unit_of_quantity = forms.ModelChoiceField(
        queryset=Unit.objects.filter(unit_type='time'),  
        widget=SelectWithPopUp(model=Unit))

    class Meta:
        model = ProcessTypeResourceType
        exclude = ('process_type', 'event_type', 'relationship')


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
