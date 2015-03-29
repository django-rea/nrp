import datetime

from django.db.models import Q
from django.http import HttpResponse, HttpResponseServerError, Http404, HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.template import RequestContext
from django.core import serializers
from django.contrib.auth.decorators import login_required
from django.core.exceptions import MultipleObjectsReturned
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.forms.models import formset_factory, modelformset_factory, inlineformset_factory, BaseModelFormSet
from django.forms import ValidationError
from django.utils import simplejson
from django.utils.datastructures import SortedDict
from django.contrib.auth.forms import UserCreationForm
from django.conf import settings

from valuenetwork.valueaccounting.models import *
from valuenetwork.equipment.forms import *

@login_required
def log_equipment_use(request, resource_id, agent_id, pattern_id):
    #import pdb; pdb.set_trace()
    equipment = get_object_or_404(EconomicResource, id=resource_id)
    context_agent = get_object_or_404(EconomicAgent, id=agent_id)
    pattern = ProcessPattern.objects.get(id=pattern_id)
    init = {"event_date": datetime.date.today()}
    equip_form = EquipmentUseForm(resource=equipment, context_agent=context_agent, initial=init, data=request.POST or None)
    if request.method == "POST":
        #import pdb; pdb.set_trace()
        if equip_form.is_valid():
            data = equip_form.cleaned_data
            input_date = data["event_date"]
            who = data["from_agent"]
            quantity = data["quantity"]
            process = Process(
                name="Print using " + equipment.identifier,
                end_date=input_date,
                start_date=input_date,
                process_pattern=pattern,
                created_by=request.user,
                context_agent=context_agent,
                started=input_date,
                finished=True,
            )
            process.save()
            usage_event = EconomicEvent(
                event_type = EventType.objects.get(name="Resource use"),
                event_date = input_date,
                resource = equipment,
                resource_type = equipment.resource_type,
                process = process,
                from_agent = who,
                to_agent = context_agent,
                context_agent = context_agent,
                quantity = quantity,
                unit_of_quantity = equipment.resource_type.unit,
                created_by = request.user,
            )
            usage_event.save()
            

    
    return render_to_response("equipment/log_equipment_use.html", {
        "equip_form": equip_form,
        "equipment": equipment,
    }, context_instance=RequestContext(request))


