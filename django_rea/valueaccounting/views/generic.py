from django.views.generic.base import ContextMixin, TemplateResponseMixin
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import (
    BaseCreateView,
    BaseDeleteView,
    BaseUpdateView,
    BaseFormView,
    DeletionMixin,
    FormMixin,
    FormMixinBase,
    ModelFormMixin,
    ProcessFormView,
)
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin, AccessMixin


class BaseReaView(TemplateResponseMixin, View):
    def get_help(self, page_name):
        from django_rea.valueaccounting.models import Help
        try:
            return Help.objects.get(page=page_name)
        except Help.DoesNotExist:
            return None

    def get_model_class(self, interface):
        """
        Gets a model implementation
        :param interface: implementation to lookup for.
        :return: An implementation or the same interface.
        """
        from django_rea.spi import ModelProvider
        try:
            return ModelProvider.get_implementation(interface)
        except KeyError:
            # TODO: check the interface is not abstract
            return interface


class BaseReaAuthenticatedView(LoginRequiredMixin, BaseReaView):
    pass

class IsSuperUserMixin(AccessMixin):
    """
    CBV mixin which verifies that the current user is a super user.
    """

    def dispatch(self, request, *args, **kwargs):
        from django.template import RequestContext
        from django.shortcuts import render_to_response

        if not request.user.is_authenticated():
            return self.handle_no_permission()
        if not request.user.is_superuser:
            return render_to_response('valueaccounting/no_permission.html', {}, context_instance=RequestContext(request))
        return super(IsSuperUserMixin, self).dispatch(request, *args, **kwargs)
