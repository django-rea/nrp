import datetime
from decimal import *

from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.forms import formset_factory
from django.forms import modelformset_factory
from django.http import Http404, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404

from django_rea.valueaccounting.forms import EconomicResourceTypeForm, ResourceTypeFacetValueForm, \
    CreateEconomicResourceForm, ResourceRoleAgentForm, AddProcessFromResourceForm, StartDateAndNameForm, \
    SendFairCoinsForm
from django_rea.valueaccounting.logic.resource import select_resource_types
from django_rea.valueaccounting.models import *
from django_rea.valueaccounting.views.generic import BaseReaAuthenticatedView, BaseReaView


def create_facet_formset(data=None):
    RtfvFormSet = formset_factory(ResourceTypeFacetValueForm, extra=0)
    init = []
    facets = Facet.objects.all()
    for facet in facets:
        d = {"facet_id": facet.id, }
        init.append(d)
    formset = RtfvFormSet(initial=init, data=data)
    for form in formset:
        id = int(form["facet_id"].value())
        facet = Facet.objects.get(id=id)
        form.facet_name = facet.name
        fvs = facet.values.all()
        choices = [('', '----------')] + [(fv.id, fv.value) for fv in fvs]
        form.fields["value"].choices = choices
    return formset


class ResourceTypesListView(BaseReaView):
    template_name = "valueaccounting/resource_types.html"

    def get(self, request):
        roots = EconomicResourceType.objects.all()
        select_all = True
        return self._render(request, roots, select_all)

    def post(self, request):
        roots = EconomicResourceType.objects.all()
        select_all = True
        selected_values = request.POST["categories"]
        if selected_values:
            vals = selected_values.split(",")
            if vals[0] == "all":
                select_all = True
                roots = EconomicResourceType.objects.all()
            else:
                select_all = False
                fvs = []
                for val in vals:
                    val_split = val.split(":")
                    fname = val_split[0]
                    fvalue = val_split[1].strip()
                    fvs.append(FacetValue.objects.get(facet__name=fname, value=fvalue))
                roots = select_resource_types(fvs)
                roots.sort(key=lambda rt: rt.label())
        return self._render(request, roots, select_all)

    def _render(self, request, roots, select_all):
        resource_names = '~'.join([
                                      res.name for res in roots])
        create_form = EconomicResourceTypeForm()
        create_formset = create_facet_formset()
        facets = Facet.objects.all()
        selected_values = "all"
        return self.render_to_response({
            "roots": roots,
            "facets": facets,
            "select_all": select_all,
            "selected_values": selected_values,
            "create_form": create_form,
            "create_formset": create_formset,
            "photo_size": (128, 128),
            "help": self.get_help("resource_types"),
            "resource_names": resource_names,
        })


class ResourceTypeView(BaseReaView):
    def _resource_role_agent_formset(prefix, data=None):
        # import pdb; pdb.set_trace()
        RraFormSet = modelformset_factory(
            AgentResourceRole,
            form=ResourceRoleAgentForm,
            can_delete=True,
            extra=4,
        )
        formset = RraFormSet(prefix=prefix, queryset=AgentResourceRole.objects.none(), data=data)
        return formset

    def get(self, request, resource_type_id):
        return self._render(request, resource_type_id)

    def post(self, request, resource_type_id):
        resource_type = get_object_or_404(EconomicResourceType, id=resource_type_id)
        agent = request.agent
        if agent:
            init = {"unit_of_quantity": resource_type.unit, }
            create_form = CreateEconomicResourceForm(
                data=request.POST or None,
                files=request.FILES or None,
                initial=init)
            if create_form.is_valid():
                resource = create_form.save(commit=False)
                resource.resource_type = resource_type
                resource.created_by = request.user
                resource.save()
                role_formset = self._resource_role_agent_formset(prefix="resource", data=request.POST)
                for form_rra in role_formset.forms:
                    if form_rra.is_valid():
                        data_rra = form_rra.cleaned_data
                        if data_rra:
                            role = data_rra["role"]
                            agent = data_rra["agent"]
                            if role and agent:
                                rra = AgentResourceRole()
                                rra.agent = agent
                                rra.role = role
                                rra.resource = resource
                                rra.is_contact = data_rra["is_contact"]
                                rra.save()
                return HttpResponseRedirect(reverse('resource', args=(resource.id,)))
        return self._render(request, resource_type_id)

    def _render(self, request, resource_type_id):
        resource_type = get_object_or_404(EconomicResourceType, id=resource_type_id)
        create_form = []
        resource_names = []
        create_role_formset = None
        agent = request.agent
        if agent:
            names = EconomicResourceType.objects.values_list('name', flat=True).exclude(id=resource_type_id)
            resource_names = '~'.join(names)
            init = {"unit_of_quantity": resource_type.unit, }
            create_form = CreateEconomicResourceForm(
                data=request.POST or None,
                files=request.FILES or None,
                initial=init)
            create_role_formset = self._resource_role_agent_formset(prefix="resource")
        return self.render_to_response({
            "resource_type": resource_type,
            "photo_size": (128, 128),
            "resource_names": resource_names,
            "agent": agent,
            "create_form": create_form,
            "create_role_formset": create_role_formset,
            "help": self.get_help("resource_type"),
        })


class ResourceView(BaseReaAuthenticatedView):
    def _render(self, request, resource_id):
        # import pdb; pdb.set_trace()
        EconomicResourceCls = self.get_model_class(EconomicResource)
        resource = get_object_or_404(EconomicResourceCls, id=resource_id)
        agent = request.agent
        RraFormSet = modelformset_factory(
            AgentResourceRole,
            form=ResourceRoleAgentForm,
            can_delete=True,
            extra=4,
        )
        role_formset = RraFormSet(
            prefix="role",
            queryset=resource.agent_resource_roles.all()
        )

        process_add_form = None
        order_form = None
        if not resource.is_digital_currency_resource():
            pattern = None
            if resource.producing_events():
                process = resource.producing_events()[0].process
                pattern = None
                if process:
                    pattern = process.process_pattern
            else:
                if agent:
                    form_data = {'name': 'Create ' + resource.identifier, 'start_date': resource.created_date,
                                 'end_date': resource.created_date}
                    process_add_form = AddProcessFromResourceForm(form_data)
                    if resource.resource_type.recipe_is_staged():
                        init = {"start_date": datetime.date.today(), }
                        order_form = StartDateAndNameForm(initial=init)

        if resource.is_digital_currency_resource():
            send_coins_form = None
            is_owner = False
            limit = 0
            if agent:
                is_owner = agent.owns(resource)
                if is_owner:
                    if resource.address_is_activated():
                        send_coins_form = SendFairCoinsForm()
                        limit = resource.spending_limit()
            self.template_name = "valueaccounting/digital_currency_resource.html"
            return self.render_to_response({
                "resource": resource,
                "photo_size": (128, 128),
                "role_formset": role_formset,
                "agent": agent,
                "is_owner": is_owner,
                "send_coins_form": send_coins_form,
                "limit": limit,
            })
        else:
            self.template_name = "valueaccounting/resource.html"
            return self.render_to_response({
                "resource": resource,
                "photo_size": (128, 128),
                "process_add_form": process_add_form,
                "order_form": order_form,
                "role_formset": role_formset,
                "agent": agent,
            })

    def get(self, request, resource_id):
        return self._render(request, resource_id)

    def post(self, request, resource_id):
        # import pdb; pdb.set_trace()
        EconomicResourceCls = self.get_model_class(EconomicResource)
        resource = get_object_or_404(EconomicResourceCls, id=resource_id)
        process_save = request.POST.get("process-save")
        if process_save:
            process_add_form = AddProcessFromResourceForm(data=request.POST)
            if process_add_form.is_valid():
                process = process_add_form.save(commit=False)
                process.started = process.start_date
                process.finished = True
                process.created_by = request.user
                process.save()
                event = EconomicEvent()
                event.context_agent = process.context_agent
                event.event_date = process.end_date
                event.event_type = process.process_pattern.event_type_for_resource_type("out",
                                                                                        resource.resource_type)
                event.process = process
                event.resource_type = resource.resource_type
                event.quantity = resource.quantity
                event.unit_of_quantity = resource.unit_of_quantity()
                event.resource = resource
                event.to_agent = event.context_agent
                event.from_agent = event.context_agent
                event.created_by = request.user
                event.save()
                return HttpResponseRedirect(reverse('resource', args=(resource.id,)))
        return self._render(request, resource_id)
