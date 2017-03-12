import datetime
from decimal import *

from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.forms import formset_factory
from django.http import Http404, HttpResponseRedirect
from django.core.urlresolvers import reverse

from django_rea.valueaccounting.forms import EconomicResourceTypeForm, ResourceTypeFacetValueForm
from django_rea.valueaccounting.logic.resource import select_resource_types
from django_rea.valueaccounting.models import *
from django_rea.valueaccounting.utils import annotate_tree_properties, project_graph
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
