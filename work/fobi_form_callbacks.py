from fobi.constants import (
    CALLBACK_BEFORE_FORM_VALIDATION,
    CALLBACK_FORM_VALID_BEFORE_SUBMIT_PLUGIN_FORM_DATA,
    CALLBACK_FORM_VALID, CALLBACK_FORM_VALID_AFTER_FORM_HANDLERS,
    CALLBACK_FORM_INVALID
    )
from fobi.base import FormCallback, form_callback_registry
from django.contrib import messages
from django.utils.translation import ugettext, ugettext_lazy as _

class JoinRequestCallback(FormCallback):
    stage = CALLBACK_BEFORE_FORM_VALIDATION

    def callback(self, form_entry, request, form):
        #print( request )
        #print( form )
        messages.info(
            request,
            _("Form {0} pre CALLBACK.").format(request.POST)
        )

        #return request
        #print("Great! Your form is valid!")

#form_callback_registry.register(JoinRequestCallback)
