from __future__ import print_function

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Location(models.Model):
    name = models.CharField(_('name'), max_length=128, unique=True)
    description = models.TextField(_('description'), blank=True, null=True)
    address = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField(default=0.0, blank=True, null=True)
    longitude = models.FloatField(default=0.0, blank=True, null=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name

    def resources(self):
        return self.resources_at_location.all()

    def agents(self):
        return self.agents_at_location.all()