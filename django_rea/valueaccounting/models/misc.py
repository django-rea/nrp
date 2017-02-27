from __future__ import print_function
from decimal import *
import datetime

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


class HomePageLayout(models.Model):
    banner = models.TextField(_('banner'), blank=True, null=True,
                              help_text=_("HTML text for top Banner"))
    use_work_panel = models.BooleanField(_('use work panel'), default=False,
                                         help_text=_("Work panel, if used, will be Panel 1"))
    work_panel_headline = models.TextField(_('work panel headline'), blank=True, null=True)
    use_needs_panel = models.BooleanField(_('use needs panel'), default=False,
                                          help_text=_("Needs panel, if used, will be Panel 2"))
    needs_panel_headline = models.TextField(_('needs panel headline'), blank=True, null=True)
    use_creations_panel = models.BooleanField(_('use creations panel'), default=False,
                                              help_text=_("Creations panel, if used, will be Panel 3"))
    creations_panel_headline = models.TextField(_('creations panel headline'), blank=True, null=True)
    panel_1 = models.TextField(_('panel 1'), blank=True, null=True,
                               help_text=_("HTML text for Panel 1"))
    panel_2 = models.TextField(_('panel 2'), blank=True, null=True,
                               help_text=_("HTML text for Panel 2"))
    panel_3 = models.TextField(_('panel 3'), blank=True, null=True,
                               help_text=_("HTML text for Panel 3"))
    footer = models.TextField(_('footer'), blank=True, null=True)

    class Meta:
        verbose_name_plural = _('home page layout')


PAGE_CHOICES = (
    ('agent', _('Agent')),
    ('agents', _('All Agents')),
    ('all_work', _('All Work')),
    ('create_distribution', _('Create Distribution')),
    ('create_exchange', _('Create Exchange')),
    ('create_sale', _('Create Sale')),
    ('demand', _('Demand')),
    ('ed_asmbly_recipe', _('Edit Assembly Recipes')),
    ('ed_wf_recipe', _('Edit Workflow Recipes')),
    ('exchange', _('Exchange')),
    ('home', _('Home')),
    ('inventory', _('Inventory')),
    ('labnotes', _('Labnotes Form')),
    ('locations', _('Locations')),
    ('associations', _('Maintain Associations')),
    ('my_work', _('My Work')),
    ('non_production', _('Non-production time logging')),
    ('projects', _('Organization')),
    ("plan_from_recipe", _('Plan from recipe')),
    ("plan_from_rt", _('Plan from Resource Type')),
    ("plan_fr_rt_rcpe", _('Plan from Resource Type Recipe')),
    ('process', _('Process')),
    ('process_select', _('Process Selections')),
    ('recipes', _('Recipes')),
    ('resource_types', _('Resource Types')),
    ('resource_type', _('Resource Type')),
    ('supply', _('Supply')),
    ('non_proc_log', _('Non-process Logging (Work)')),
    ('proc_log', _('Process Logging (Work)')),
    ('profile', _('My Profile (Work)')),
    ('my_history', _('My History (Work)')),
    ('work_map', _('Map (Work)')),
    ('work_home', _('Home (Work)')),
    ('process_work', _('Process (Work)')),
    ('work_timer', _('Work Now (Work)')),
)


@python_2_unicode_compatible
class Help(models.Model):
    page = models.CharField(_('page'), max_length=16, choices=PAGE_CHOICES, unique=True)
    description = models.TextField(_('description'), blank=True, null=True)

    class Meta:
        verbose_name_plural = _('help')
        ordering = ('page',)

    def __str__(self):
        return self.get_page_display()
