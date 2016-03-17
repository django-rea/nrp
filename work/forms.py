import sys
import datetime
from decimal import *
from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from valuenetwork.valueaccounting.models import *

class UploadAgentForm(forms.ModelForm):
    photo_url = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'url input-xxlarge',}))
    
    class Meta:
        model = EconomicAgent
        fields = ('photo', 'photo_url')
