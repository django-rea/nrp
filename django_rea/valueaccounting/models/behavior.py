from __future__ import print_function
from decimal import *
import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _


class DistributionManager(models.Manager):
    def distributions(self, start=None, end=None):
        if start and end:
            dists = Distribution.objects.filter(distribution_date__range=[start, end])
        else:
            dists = Distribution.objects.all()
        return dists


@python_2_unicode_compatible
class Distribution(models.Model):
    name = models.CharField(_('name'), blank=True, max_length=128)
    process_pattern = models.ForeignKey(ProcessPattern,
                                        blank=True, null=True,
                                        verbose_name=_('pattern'), related_name='distributions')
    context_agent = models.ForeignKey("EconomicAgent",
                                      blank=True, null=True,
                                      limit_choices_to={"is_context": True, },
                                      verbose_name=_('context agent'), related_name='distributions')
    url = models.CharField(_('url'), max_length=255, blank=True, null=True)
    distribution_date = models.DateField(_('distribution date'))
    notes = models.TextField(_('notes'), blank=True)
    value_equation = models.ForeignKey(ValueEquation,
                                       blank=True, null=True,
                                       verbose_name=_('value equation link'), related_name='distributions')
    value_equation_content = models.TextField(_('value equation formulas used'), null=True, blank=True)
    created_by = models.ForeignKey(User, verbose_name=_('created by'),
                                   related_name='distributions_created', blank=True, null=True, editable=False)
    changed_by = models.ForeignKey(User, verbose_name=_('changed by'),
                                   related_name='distributions_changed', blank=True, null=True, editable=False)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True, editable=False)
    changed_date = models.DateField(auto_now=True, blank=True, null=True, editable=False)
    slug = models.SlugField(_("Page name"), editable=False)

    objects = DistributionManager()

    class Meta:
        ordering = ('-distribution_date',)
        verbose_name_plural = _("distributions")

    def __str__(self):
        show_name = "Distribution"
        name = ""
        if self.name:
            name = self.name + ","
        return " ".join([
            name,
            show_name,
            "starting",
            self.distribution_date.strftime('%Y-%m-%d'),
        ])

    def deserialize_value_equation_content(self):
        return simplejson.loads(self.value_equation_content)

    def buckets(self):
        dict = self.deserialize_value_equation_content()
        bucket_dict = dict["buckets"]
        buckets = []
        for key, value in bucket_dict.iteritems():
            bucket = ValueEquationBucket.objects.get(id=key)
            bucket.value = value
            buckets.append(bucket)
        return buckets

    def bucket_rules(self):
        buckets = self.buckets()
        answer = []
        for bucket in buckets:
            rules = bucket.value.get("bucket_rules")
            if rules:
                for key, value in rules.iteritems():
                    rule = ValueEquationBucketRule.objects.get(id=key)
                    rule.value = value
                    answer.append(rule)
        return answer

    def orders(self):
        buckets = self.buckets()
        orders = []
        for b in buckets:
            filter = b.value.get("filter")
            if filter:
                method = filter.get("method")
                if method:
                    if method == "Order":
                        oids = filter["orders"]
                        for oid in oids:
                            orders.append(Order.objects.get(id=oid))
        return orders

    def shipments(self):
        buckets = self.buckets()
        shipments = []
        for b in buckets:
            filter = b.value.get("filter")
            if filter:
                method = filter.get("method")
                if method:
                    if method == "Shipment":
                        ship_ids = filter["shipments"]
                        for sid in ship_ids:
                            shipments.append(EconomicEvent.objects.get(id=sid))
        return shipments

    def distribution_events(self):
        return self.events.filter(
            event_type__relationship='distribute')

    def disbursement_events(self):
        return self.events.filter(
            event_type__relationship='disburse')

    def distribution_total(self):
        dists = self.distribution_events()
        total = 0
        for dist in dists:
            total += dist.quantity
        return total

    def disbursement_total(self):
        disbs = self.disbursement_events()
        total = 0
        for disb in disbs:
            total += disb.quantity
        return total

    def flow_type(self):
        return "Distribution"

    def flow_class(self):
        return "distribution"

    def flow_description(self):
        return self.__str__()
