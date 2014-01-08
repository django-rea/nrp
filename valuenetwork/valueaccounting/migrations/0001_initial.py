# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Help'
        db.create_table('valueaccounting_help', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('page', self.gf('django.db.models.fields.CharField')(unique=True, max_length=16)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('valueaccounting', ['Help'])

        # Adding model 'Facet'
        db.create_table('valueaccounting_facet', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('valueaccounting', ['Facet'])

        # Adding model 'FacetValue'
        db.create_table('valueaccounting_facetvalue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('facet', self.gf('django.db.models.fields.related.ForeignKey')(related_name='values', to=orm['valueaccounting.Facet'])),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('valueaccounting', ['FacetValue'])

        # Adding unique constraint on 'FacetValue', fields ['facet', 'value']
        db.create_unique('valueaccounting_facetvalue', ['facet_id', 'value'])

        # Adding model 'Unit'
        db.create_table('valueaccounting_unit', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('unit_type', self.gf('django.db.models.fields.CharField')(max_length=12)),
            ('abbrev', self.gf('django.db.models.fields.CharField')(max_length=8)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('symbol', self.gf('django.db.models.fields.CharField')(max_length=1, blank=True)),
        ))
        db.send_create_signal('valueaccounting', ['Unit'])

        # Adding model 'AgentType'
        db.create_table('valueaccounting_agenttype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='sub-agents', null=True, to=orm['valueaccounting.AgentType'])),
            ('member_type', self.gf('django.db.models.fields.CharField')(default='active', max_length=12)),
            ('party_type', self.gf('django.db.models.fields.CharField')(default='individual', max_length=12)),
        ))
        db.send_create_signal('valueaccounting', ['AgentType'])

        # Adding model 'EconomicAgent'
        db.create_table('valueaccounting_economicagent', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('nick', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('agent_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='agents', to=orm['valueaccounting.AgentType'])),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=96, null=True, blank=True)),
            ('latitude', self.gf('django.db.models.fields.FloatField')(default=0.0, null=True, blank=True)),
            ('longitude', self.gf('django.db.models.fields.FloatField')(default=0.0, null=True, blank=True)),
            ('reputation', self.gf('django.db.models.fields.DecimalField')(default='0.00', max_digits=8, decimal_places=2)),
            ('photo', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('photo_url', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
            ('created_date', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='agents_created', null=True, to=orm['auth.User'])),
            ('changed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='agents_changed', null=True, to=orm['auth.User'])),
            ('changed_date', self.gf('django.db.models.fields.DateField')(auto_now=True, null=True, blank=True)),
        ))
        db.send_create_signal('valueaccounting', ['EconomicAgent'])

        # Adding model 'AgentUser'
        db.create_table('valueaccounting_agentuser', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('agent', self.gf('django.db.models.fields.related.ForeignKey')(related_name='users', to=orm['valueaccounting.EconomicAgent'])),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='agent', unique=True, to=orm['auth.User'])),
        ))
        db.send_create_signal('valueaccounting', ['AgentUser'])

        # Adding model 'AssociationType'
        db.create_table('valueaccounting_associationtype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal('valueaccounting', ['AssociationType'])

        # Adding model 'AgentAssociation'
        db.create_table('valueaccounting_agentassociation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('from_agent', self.gf('django.db.models.fields.related.ForeignKey')(related_name='associations_from', to=orm['valueaccounting.EconomicAgent'])),
            ('to_agent', self.gf('django.db.models.fields.related.ForeignKey')(related_name='associations_to', to=orm['valueaccounting.EconomicAgent'])),
            ('association_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='associations', to=orm['valueaccounting.AssociationType'])),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('valueaccounting', ['AgentAssociation'])

        # Adding model 'EventType'
        db.create_table('valueaccounting_eventtype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('inverse_label', self.gf('django.db.models.fields.CharField')(max_length=40, blank=True)),
            ('relationship', self.gf('django.db.models.fields.CharField')(default='in', max_length=12)),
            ('related_to', self.gf('django.db.models.fields.CharField')(default='process', max_length=12)),
            ('resource_effect', self.gf('django.db.models.fields.CharField')(max_length=12)),
            ('unit_type', self.gf('django.db.models.fields.CharField')(max_length=12, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
        ))
        db.send_create_signal('valueaccounting', ['EventType'])

        # Adding model 'EconomicResourceType'
        db.create_table('valueaccounting_economicresourcetype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='children', null=True, to=orm['valueaccounting.EconomicResourceType'])),
            ('unit', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='resource_units', null=True, to=orm['valueaccounting.Unit'])),
            ('unit_of_use', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='units_of_use', null=True, to=orm['valueaccounting.Unit'])),
            ('photo', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('photo_url', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('rate', self.gf('django.db.models.fields.DecimalField')(default='0.00', max_digits=6, decimal_places=2)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='resource_types_created', null=True, to=orm['auth.User'])),
            ('changed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='resource_types_changed', null=True, to=orm['auth.User'])),
            ('created_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, null=True, blank=True)),
            ('changed_date', self.gf('django.db.models.fields.DateField')(auto_now=True, null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
        ))
        db.send_create_signal('valueaccounting', ['EconomicResourceType'])

        # Adding model 'ResourceTypeFacetValue'
        db.create_table('valueaccounting_resourcetypefacetvalue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('resource_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='facets', to=orm['valueaccounting.EconomicResourceType'])),
            ('facet_value', self.gf('django.db.models.fields.related.ForeignKey')(related_name='resource_types', to=orm['valueaccounting.FacetValue'])),
        ))
        db.send_create_signal('valueaccounting', ['ResourceTypeFacetValue'])

        # Adding unique constraint on 'ResourceTypeFacetValue', fields ['resource_type', 'facet_value']
        db.create_unique('valueaccounting_resourcetypefacetvalue', ['resource_type_id', 'facet_value_id'])

        # Adding model 'ProcessPattern'
        db.create_table('valueaccounting_processpattern', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=32)),
        ))
        db.send_create_signal('valueaccounting', ['ProcessPattern'])

        # Adding model 'PatternFacetValue'
        db.create_table('valueaccounting_patternfacetvalue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pattern', self.gf('django.db.models.fields.related.ForeignKey')(related_name='facets', to=orm['valueaccounting.ProcessPattern'])),
            ('facet_value', self.gf('django.db.models.fields.related.ForeignKey')(related_name='patterns', to=orm['valueaccounting.FacetValue'])),
            ('event_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='patterns', to=orm['valueaccounting.EventType'])),
        ))
        db.send_create_signal('valueaccounting', ['PatternFacetValue'])

        # Adding unique constraint on 'PatternFacetValue', fields ['pattern', 'facet_value', 'event_type']
        db.create_unique('valueaccounting_patternfacetvalue', ['pattern_id', 'facet_value_id', 'event_type_id'])

        # Adding model 'UseCase'
        db.create_table('valueaccounting_usecase', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('identifier', self.gf('django.db.models.fields.CharField')(max_length=12)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('restrict_to_one_pattern', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('valueaccounting', ['UseCase'])

        # Adding model 'PatternUseCase'
        db.create_table('valueaccounting_patternusecase', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('pattern', self.gf('django.db.models.fields.related.ForeignKey')(related_name='use_cases', to=orm['valueaccounting.ProcessPattern'])),
            ('use_case', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='patterns', null=True, to=orm['valueaccounting.UseCase'])),
        ))
        db.send_create_signal('valueaccounting', ['PatternUseCase'])

        # Adding model 'EconomicResource'
        db.create_table('valueaccounting_economicresource', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('resource_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='resources', to=orm['valueaccounting.EconomicResourceType'])),
            ('identifier', self.gf('django.db.models.fields.CharField')(max_length=128, blank=True)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('author', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='authored_resources', null=True, to=orm['valueaccounting.EconomicAgent'])),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='owned_resources', null=True, to=orm['valueaccounting.EconomicAgent'])),
            ('custodian', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='custody_resources', null=True, to=orm['valueaccounting.EconomicAgent'])),
            ('quantity', self.gf('django.db.models.fields.DecimalField')(default='1.00', max_digits=8, decimal_places=2)),
            ('unit_of_quantity', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='resource_qty_units', null=True, to=orm['valueaccounting.Unit'])),
            ('quality', self.gf('django.db.models.fields.DecimalField')(default='0', null=True, max_digits=3, decimal_places=0, blank=True)),
            ('notes', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('photo', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('photo_url', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('created_date', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='resources_created', null=True, to=orm['auth.User'])),
            ('changed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='resources_changed', null=True, to=orm['auth.User'])),
            ('changed_date', self.gf('django.db.models.fields.DateField')(auto_now=True, null=True, blank=True)),
        ))
        db.send_create_signal('valueaccounting', ['EconomicResource'])

        # Adding model 'AgentResourceType'
        db.create_table('valueaccounting_agentresourcetype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('agent', self.gf('django.db.models.fields.related.ForeignKey')(related_name='resource_types', to=orm['valueaccounting.EconomicAgent'])),
            ('resource_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='agents', to=orm['valueaccounting.EconomicResourceType'])),
            ('score', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=8, decimal_places=2)),
            ('event_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='agent_resource_types', to=orm['valueaccounting.EventType'])),
            ('lead_time', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('value', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=8, decimal_places=2)),
            ('unit_of_value', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='agent_resource_value_units', null=True, to=orm['valueaccounting.Unit'])),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='arts_created', null=True, to=orm['auth.User'])),
            ('changed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='arts_changed', null=True, to=orm['auth.User'])),
            ('created_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, null=True, blank=True)),
            ('changed_date', self.gf('django.db.models.fields.DateField')(auto_now=True, null=True, blank=True)),
        ))
        db.send_create_signal('valueaccounting', ['AgentResourceType'])

        # Adding model 'Project'
        db.create_table('valueaccounting_project', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='sub_projects', null=True, to=orm['valueaccounting.Project'])),
            ('project_team', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='project_team', null=True, to=orm['valueaccounting.EconomicAgent'])),
            ('importance', self.gf('django.db.models.fields.DecimalField')(default='0', max_digits=3, decimal_places=0)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='projects_created', null=True, to=orm['auth.User'])),
            ('changed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='projects_changed', null=True, to=orm['auth.User'])),
            ('created_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, null=True, blank=True)),
            ('changed_date', self.gf('django.db.models.fields.DateField')(auto_now=True, null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
        ))
        db.send_create_signal('valueaccounting', ['Project'])

        # Adding model 'ProcessType'
        db.create_table('valueaccounting_processtype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='sub_process_types', null=True, to=orm['valueaccounting.ProcessType'])),
            ('process_pattern', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='process_types', null=True, to=orm['valueaccounting.ProcessPattern'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='process_types', null=True, to=orm['valueaccounting.Project'])),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('estimated_duration', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='process_types_created', null=True, to=orm['auth.User'])),
            ('changed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='process_types_changed', null=True, to=orm['auth.User'])),
            ('created_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, null=True, blank=True)),
            ('changed_date', self.gf('django.db.models.fields.DateField')(auto_now=True, null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
        ))
        db.send_create_signal('valueaccounting', ['ProcessType'])

        # Adding model 'ProcessTypeResourceType'
        db.create_table('valueaccounting_processtyperesourcetype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('process_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='resource_types', to=orm['valueaccounting.ProcessType'])),
            ('resource_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='process_types', to=orm['valueaccounting.EconomicResourceType'])),
            ('event_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='process_resource_types', to=orm['valueaccounting.EventType'])),
            ('quantity', self.gf('django.db.models.fields.DecimalField')(default='0.00', max_digits=8, decimal_places=2)),
            ('unit_of_quantity', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='process_resource_qty_units', null=True, to=orm['valueaccounting.Unit'])),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='ptrts_created', null=True, to=orm['auth.User'])),
            ('changed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='ptrts_changed', null=True, to=orm['auth.User'])),
            ('created_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, null=True, blank=True)),
            ('changed_date', self.gf('django.db.models.fields.DateField')(auto_now=True, null=True, blank=True)),
        ))
        db.send_create_signal('valueaccounting', ['ProcessTypeResourceType'])

        # Adding model 'Process'
        db.create_table('valueaccounting_process', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='sub_processes', null=True, to=orm['valueaccounting.Process'])),
            ('process_pattern', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='processes', null=True, to=orm['valueaccounting.ProcessPattern'])),
            ('process_type', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='processes', null=True, on_delete=models.SET_NULL, to=orm['valueaccounting.ProcessType'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='processes', null=True, to=orm['valueaccounting.Project'])),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('start_date', self.gf('django.db.models.fields.DateField')()),
            ('end_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('started', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('finished', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('managed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='managed_processes', null=True, to=orm['valueaccounting.EconomicAgent'])),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='owned_processes', null=True, to=orm['valueaccounting.EconomicAgent'])),
            ('notes', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='processes_created', null=True, to=orm['auth.User'])),
            ('changed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='processes_changed', null=True, to=orm['auth.User'])),
            ('created_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, null=True, blank=True)),
            ('changed_date', self.gf('django.db.models.fields.DateField')(auto_now=True, null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
        ))
        db.send_create_signal('valueaccounting', ['Process'])

        # Adding model 'Exchange'
        db.create_table('valueaccounting_exchange', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('process_pattern', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='exchanges', null=True, to=orm['valueaccounting.ProcessPattern'])),
            ('use_case', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='exchanges', null=True, to=orm['valueaccounting.UseCase'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='exchanges', null=True, to=orm['valueaccounting.Project'])),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('start_date', self.gf('django.db.models.fields.DateField')()),
            ('end_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('notes', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='exchanges_created', null=True, to=orm['auth.User'])),
            ('changed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='exchanges_changed', null=True, to=orm['auth.User'])),
            ('created_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, null=True, blank=True)),
            ('changed_date', self.gf('django.db.models.fields.DateField')(auto_now=True, null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
        ))
        db.send_create_signal('valueaccounting', ['Exchange'])

        # Adding model 'Feature'
        db.create_table('valueaccounting_feature', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('product', self.gf('django.db.models.fields.related.ForeignKey')(related_name='features', to=orm['valueaccounting.EconomicResourceType'])),
            ('process_type', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='features', null=True, to=orm['valueaccounting.ProcessType'])),
            ('event_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='features', to=orm['valueaccounting.EventType'])),
            ('quantity', self.gf('django.db.models.fields.DecimalField')(default='0.00', max_digits=8, decimal_places=2)),
            ('unit_of_quantity', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='feature_units', null=True, to=orm['valueaccounting.Unit'])),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='features_created', null=True, to=orm['auth.User'])),
            ('changed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='features_changed', null=True, to=orm['auth.User'])),
            ('created_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, null=True, blank=True)),
            ('changed_date', self.gf('django.db.models.fields.DateField')(auto_now=True, null=True, blank=True)),
        ))
        db.send_create_signal('valueaccounting', ['Feature'])

        # Adding model 'Option'
        db.create_table('valueaccounting_option', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('feature', self.gf('django.db.models.fields.related.ForeignKey')(related_name='options', to=orm['valueaccounting.Feature'])),
            ('component', self.gf('django.db.models.fields.related.ForeignKey')(related_name='options', to=orm['valueaccounting.EconomicResourceType'])),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='options_created', null=True, to=orm['auth.User'])),
            ('changed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='options_changed', null=True, to=orm['auth.User'])),
            ('created_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, null=True, blank=True)),
            ('changed_date', self.gf('django.db.models.fields.DateField')(auto_now=True, null=True, blank=True)),
        ))
        db.send_create_signal('valueaccounting', ['Option'])

        # Adding model 'Order'
        db.create_table('valueaccounting_order', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order_type', self.gf('django.db.models.fields.CharField')(default='customer', max_length=12)),
            ('receiver', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='purchase_orders', null=True, to=orm['valueaccounting.EconomicAgent'])),
            ('provider', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='sales_orders', null=True, to=orm['valueaccounting.EconomicAgent'])),
            ('order_date', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
            ('due_date', self.gf('django.db.models.fields.DateField')()),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='orders_created', null=True, to=orm['auth.User'])),
            ('changed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='orders_changed', null=True, to=orm['auth.User'])),
            ('created_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, null=True, blank=True)),
            ('changed_date', self.gf('django.db.models.fields.DateField')(auto_now=True, null=True, blank=True)),
        ))
        db.send_create_signal('valueaccounting', ['Order'])

        # Adding model 'Commitment'
        db.create_table('valueaccounting_commitment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='commitments', null=True, to=orm['valueaccounting.Order'])),
            ('independent_demand', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='dependent_commitments', null=True, to=orm['valueaccounting.Order'])),
            ('event_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='commitments', to=orm['valueaccounting.EventType'])),
            ('commitment_date', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
            ('start_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('due_date', self.gf('django.db.models.fields.DateField')()),
            ('finished', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('from_agent_type', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='given_commitments', null=True, to=orm['valueaccounting.AgentType'])),
            ('from_agent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='given_commitments', null=True, to=orm['valueaccounting.EconomicAgent'])),
            ('to_agent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='taken_commitments', null=True, to=orm['valueaccounting.EconomicAgent'])),
            ('resource_type', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='commitments', null=True, to=orm['valueaccounting.EconomicResourceType'])),
            ('resource', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='commitments', null=True, to=orm['valueaccounting.EconomicResource'])),
            ('process', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='commitments', null=True, to=orm['valueaccounting.Process'])),
            ('exchange', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='commitments', null=True, to=orm['valueaccounting.Exchange'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='commitments', null=True, to=orm['valueaccounting.Project'])),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('quantity', self.gf('django.db.models.fields.DecimalField')(max_digits=8, decimal_places=2)),
            ('unit_of_quantity', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='commitment_qty_units', null=True, to=orm['valueaccounting.Unit'])),
            ('quality', self.gf('django.db.models.fields.DecimalField')(default='0', max_digits=3, decimal_places=0)),
            ('value', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=8, decimal_places=2)),
            ('unit_of_value', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='commitment_value_units', null=True, to=orm['valueaccounting.Unit'])),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='commitments_created', null=True, to=orm['auth.User'])),
            ('changed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='commitments_changed', null=True, to=orm['auth.User'])),
            ('created_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, null=True, blank=True)),
            ('changed_date', self.gf('django.db.models.fields.DateField')(auto_now=True, null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
        ))
        db.send_create_signal('valueaccounting', ['Commitment'])

        # Adding model 'Reciprocity'
        db.create_table('valueaccounting_reciprocity', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('initiating_commitment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='initiated_commitments', to=orm['valueaccounting.Commitment'])),
            ('reciprocal_commitment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='reciprocal_commitments', to=orm['valueaccounting.Commitment'])),
            ('reciprocity_date', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
        ))
        db.send_create_signal('valueaccounting', ['Reciprocity'])

        # Adding model 'SelectedOption'
        db.create_table('valueaccounting_selectedoption', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('commitment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='options', to=orm['valueaccounting.Commitment'])),
            ('option', self.gf('django.db.models.fields.related.ForeignKey')(related_name='commitments', to=orm['valueaccounting.Option'])),
        ))
        db.send_create_signal('valueaccounting', ['SelectedOption'])

        # Adding model 'EconomicEvent'
        db.create_table('valueaccounting_economicevent', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('event_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='events', to=orm['valueaccounting.EventType'])),
            ('event_date', self.gf('django.db.models.fields.DateField')()),
            ('from_agent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='given_events', null=True, to=orm['valueaccounting.EconomicAgent'])),
            ('to_agent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='taken_events', null=True, to=orm['valueaccounting.EconomicAgent'])),
            ('resource_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='events', to=orm['valueaccounting.EconomicResourceType'])),
            ('resource', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='events', null=True, to=orm['valueaccounting.EconomicResource'])),
            ('process', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='events', null=True, on_delete=models.SET_NULL, to=orm['valueaccounting.Process'])),
            ('exchange', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='events', null=True, on_delete=models.SET_NULL, to=orm['valueaccounting.Exchange'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='events', null=True, on_delete=models.SET_NULL, to=orm['valueaccounting.Project'])),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('quantity', self.gf('django.db.models.fields.DecimalField')(max_digits=8, decimal_places=2)),
            ('unit_of_quantity', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='event_qty_units', null=True, to=orm['valueaccounting.Unit'])),
            ('quality', self.gf('django.db.models.fields.DecimalField')(default='0', max_digits=3, decimal_places=0)),
            ('value', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=8, decimal_places=2)),
            ('unit_of_value', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='event_value_units', null=True, to=orm['valueaccounting.Unit'])),
            ('commitment', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='fulfillment_events', null=True, on_delete=models.SET_NULL, to=orm['valueaccounting.Commitment'])),
            ('is_contribution', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='events_created', null=True, to=orm['auth.User'])),
            ('changed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='events_changed', null=True, to=orm['auth.User'])),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
        ))
        db.send_create_signal('valueaccounting', ['EconomicEvent'])

        # Adding model 'Compensation'
        db.create_table('valueaccounting_compensation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('initiating_event', self.gf('django.db.models.fields.related.ForeignKey')(related_name='initiated_compensations', to=orm['valueaccounting.EconomicEvent'])),
            ('compensating_event', self.gf('django.db.models.fields.related.ForeignKey')(related_name='compensations', to=orm['valueaccounting.EconomicEvent'])),
            ('compensation_date', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
            ('compensating_value', self.gf('django.db.models.fields.DecimalField')(max_digits=8, decimal_places=2)),
        ))
        db.send_create_signal('valueaccounting', ['Compensation'])

        # Adding model 'CachedEventSummary'
        db.create_table('valueaccounting_cachedeventsummary', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('agent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='cached_events', null=True, to=orm['valueaccounting.EconomicAgent'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='cached_events', null=True, to=orm['valueaccounting.Project'])),
            ('resource_type', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='cached_events', null=True, to=orm['valueaccounting.EconomicResourceType'])),
            ('resource_type_rate', self.gf('django.db.models.fields.DecimalField')(default='1.0', max_digits=8, decimal_places=2)),
            ('importance', self.gf('django.db.models.fields.DecimalField')(default='1', max_digits=3, decimal_places=0)),
            ('reputation', self.gf('django.db.models.fields.DecimalField')(default='1.00', max_digits=8, decimal_places=2)),
            ('quantity', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=8, decimal_places=2)),
            ('value', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=8, decimal_places=2)),
        ))
        db.send_create_signal('valueaccounting', ['CachedEventSummary'])


    def backwards(self, orm):
        # Removing unique constraint on 'PatternFacetValue', fields ['pattern', 'facet_value', 'event_type']
        db.delete_unique('valueaccounting_patternfacetvalue', ['pattern_id', 'facet_value_id', 'event_type_id'])

        # Removing unique constraint on 'ResourceTypeFacetValue', fields ['resource_type', 'facet_value']
        db.delete_unique('valueaccounting_resourcetypefacetvalue', ['resource_type_id', 'facet_value_id'])

        # Removing unique constraint on 'FacetValue', fields ['facet', 'value']
        db.delete_unique('valueaccounting_facetvalue', ['facet_id', 'value'])

        # Deleting model 'Help'
        db.delete_table('valueaccounting_help')

        # Deleting model 'Facet'
        db.delete_table('valueaccounting_facet')

        # Deleting model 'FacetValue'
        db.delete_table('valueaccounting_facetvalue')

        # Deleting model 'Unit'
        db.delete_table('valueaccounting_unit')

        # Deleting model 'AgentType'
        db.delete_table('valueaccounting_agenttype')

        # Deleting model 'EconomicAgent'
        db.delete_table('valueaccounting_economicagent')

        # Deleting model 'AgentUser'
        db.delete_table('valueaccounting_agentuser')

        # Deleting model 'AssociationType'
        db.delete_table('valueaccounting_associationtype')

        # Deleting model 'AgentAssociation'
        db.delete_table('valueaccounting_agentassociation')

        # Deleting model 'EventType'
        db.delete_table('valueaccounting_eventtype')

        # Deleting model 'EconomicResourceType'
        db.delete_table('valueaccounting_economicresourcetype')

        # Deleting model 'ResourceTypeFacetValue'
        db.delete_table('valueaccounting_resourcetypefacetvalue')

        # Deleting model 'ProcessPattern'
        db.delete_table('valueaccounting_processpattern')

        # Deleting model 'PatternFacetValue'
        db.delete_table('valueaccounting_patternfacetvalue')

        # Deleting model 'UseCase'
        db.delete_table('valueaccounting_usecase')

        # Deleting model 'PatternUseCase'
        db.delete_table('valueaccounting_patternusecase')

        # Deleting model 'EconomicResource'
        db.delete_table('valueaccounting_economicresource')

        # Deleting model 'AgentResourceType'
        db.delete_table('valueaccounting_agentresourcetype')

        # Deleting model 'Project'
        db.delete_table('valueaccounting_project')

        # Deleting model 'ProcessType'
        db.delete_table('valueaccounting_processtype')

        # Deleting model 'ProcessTypeResourceType'
        db.delete_table('valueaccounting_processtyperesourcetype')

        # Deleting model 'Process'
        db.delete_table('valueaccounting_process')

        # Deleting model 'Exchange'
        db.delete_table('valueaccounting_exchange')

        # Deleting model 'Feature'
        db.delete_table('valueaccounting_feature')

        # Deleting model 'Option'
        db.delete_table('valueaccounting_option')

        # Deleting model 'Order'
        db.delete_table('valueaccounting_order')

        # Deleting model 'Commitment'
        db.delete_table('valueaccounting_commitment')

        # Deleting model 'Reciprocity'
        db.delete_table('valueaccounting_reciprocity')

        # Deleting model 'SelectedOption'
        db.delete_table('valueaccounting_selectedoption')

        # Deleting model 'EconomicEvent'
        db.delete_table('valueaccounting_economicevent')

        # Deleting model 'Compensation'
        db.delete_table('valueaccounting_compensation')

        # Deleting model 'CachedEventSummary'
        db.delete_table('valueaccounting_cachedeventsummary')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'valueaccounting.agentassociation': {
            'Meta': {'object_name': 'AgentAssociation'},
            'association_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'associations'", 'to': "orm['valueaccounting.AssociationType']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'from_agent': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'associations_from'", 'to': "orm['valueaccounting.EconomicAgent']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_agent': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'associations_to'", 'to': "orm['valueaccounting.EconomicAgent']"})
        },
        'valueaccounting.agentresourcetype': {
            'Meta': {'object_name': 'AgentResourceType'},
            'agent': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resource_types'", 'to': "orm['valueaccounting.EconomicAgent']"}),
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'arts_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'arts_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'event_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'agent_resource_types'", 'to': "orm['valueaccounting.EventType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lead_time': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'resource_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'agents'", 'to': "orm['valueaccounting.EconomicResourceType']"}),
            'score': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '8', 'decimal_places': '2'}),
            'unit_of_value': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'agent_resource_value_units'", 'null': 'True', 'to': "orm['valueaccounting.Unit']"}),
            'value': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '8', 'decimal_places': '2'})
        },
        'valueaccounting.agenttype': {
            'Meta': {'ordering': "('name',)", 'object_name': 'AgentType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'member_type': ('django.db.models.fields.CharField', [], {'default': "'active'", 'max_length': '12'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'sub-agents'", 'null': 'True', 'to': "orm['valueaccounting.AgentType']"}),
            'party_type': ('django.db.models.fields.CharField', [], {'default': "'individual'", 'max_length': '12'})
        },
        'valueaccounting.agentuser': {
            'Meta': {'object_name': 'AgentUser'},
            'agent': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users'", 'to': "orm['valueaccounting.EconomicAgent']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'agent'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'valueaccounting.associationtype': {
            'Meta': {'object_name': 'AssociationType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'valueaccounting.cachedeventsummary': {
            'Meta': {'ordering': "('agent', 'project', 'resource_type')", 'object_name': 'CachedEventSummary'},
            'agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'cached_events'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'importance': ('django.db.models.fields.DecimalField', [], {'default': "'1'", 'max_digits': '3', 'decimal_places': '0'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'cached_events'", 'null': 'True', 'to': "orm['valueaccounting.Project']"}),
            'quantity': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '8', 'decimal_places': '2'}),
            'reputation': ('django.db.models.fields.DecimalField', [], {'default': "'1.00'", 'max_digits': '8', 'decimal_places': '2'}),
            'resource_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'cached_events'", 'null': 'True', 'to': "orm['valueaccounting.EconomicResourceType']"}),
            'resource_type_rate': ('django.db.models.fields.DecimalField', [], {'default': "'1.0'", 'max_digits': '8', 'decimal_places': '2'}),
            'value': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '8', 'decimal_places': '2'})
        },
        'valueaccounting.commitment': {
            'Meta': {'ordering': "('due_date',)", 'object_name': 'Commitment'},
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitments_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'commitment_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitments_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'due_date': ('django.db.models.fields.DateField', [], {}),
            'event_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'commitments'", 'to': "orm['valueaccounting.EventType']"}),
            'exchange': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitments'", 'null': 'True', 'to': "orm['valueaccounting.Exchange']"}),
            'finished': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'from_agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'given_commitments'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'from_agent_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'given_commitments'", 'null': 'True', 'to': "orm['valueaccounting.AgentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'independent_demand': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'dependent_commitments'", 'null': 'True', 'to': "orm['valueaccounting.Order']"}),
            'order': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitments'", 'null': 'True', 'to': "orm['valueaccounting.Order']"}),
            'process': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitments'", 'null': 'True', 'to': "orm['valueaccounting.Process']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitments'", 'null': 'True', 'to': "orm['valueaccounting.Project']"}),
            'quality': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '3', 'decimal_places': '0'}),
            'quantity': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitments'", 'null': 'True', 'to': "orm['valueaccounting.EconomicResource']"}),
            'resource_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitments'", 'null': 'True', 'to': "orm['valueaccounting.EconomicResourceType']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'to_agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'taken_commitments'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'unit_of_quantity': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitment_qty_units'", 'null': 'True', 'to': "orm['valueaccounting.Unit']"}),
            'unit_of_value': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitment_value_units'", 'null': 'True', 'to': "orm['valueaccounting.Unit']"}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'value': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '8', 'decimal_places': '2'})
        },
        'valueaccounting.compensation': {
            'Meta': {'ordering': "('compensation_date',)", 'object_name': 'Compensation'},
            'compensating_event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'compensations'", 'to': "orm['valueaccounting.EconomicEvent']"}),
            'compensating_value': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'compensation_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initiating_event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'initiated_compensations'", 'to': "orm['valueaccounting.EconomicEvent']"})
        },
        'valueaccounting.economicagent': {
            'Meta': {'ordering': "('nick',)", 'object_name': 'EconomicAgent'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'agent_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'agents'", 'to': "orm['valueaccounting.AgentType']"}),
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'agents_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'agents_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '96', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latitude': ('django.db.models.fields.FloatField', [], {'default': '0.0', 'null': 'True', 'blank': 'True'}),
            'longitude': ('django.db.models.fields.FloatField', [], {'default': '0.0', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'nick': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'photo_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'reputation': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '8', 'decimal_places': '2'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'valueaccounting.economicevent': {
            'Meta': {'ordering': "('-event_date',)", 'object_name': 'EconomicEvent'},
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'commitment': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'fulfillment_events'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['valueaccounting.Commitment']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'event_date': ('django.db.models.fields.DateField', [], {}),
            'event_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'events'", 'to': "orm['valueaccounting.EventType']"}),
            'exchange': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['valueaccounting.Exchange']"}),
            'from_agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'given_events'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_contribution': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'process': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['valueaccounting.Process']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['valueaccounting.Project']"}),
            'quality': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '3', 'decimal_places': '0'}),
            'quantity': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'to': "orm['valueaccounting.EconomicResource']"}),
            'resource_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'events'", 'to': "orm['valueaccounting.EconomicResourceType']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'to_agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'taken_events'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'unit_of_quantity': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'event_qty_units'", 'null': 'True', 'to': "orm['valueaccounting.Unit']"}),
            'unit_of_value': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'event_value_units'", 'null': 'True', 'to': "orm['valueaccounting.Unit']"}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'value': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '8', 'decimal_places': '2'})
        },
        'valueaccounting.economicresource': {
            'Meta': {'ordering': "('resource_type', 'identifier')", 'object_name': 'EconomicResource'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'authored_resources'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'resources_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'resources_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'custodian': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'custody_resources'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_resources'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'photo_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'quality': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'null': 'True', 'max_digits': '3', 'decimal_places': '0', 'blank': 'True'}),
            'quantity': ('django.db.models.fields.DecimalField', [], {'default': "'1.00'", 'max_digits': '8', 'decimal_places': '2'}),
            'resource_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': "orm['valueaccounting.EconomicResourceType']"}),
            'unit_of_quantity': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'resource_qty_units'", 'null': 'True', 'to': "orm['valueaccounting.Unit']"}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'valueaccounting.economicresourcetype': {
            'Meta': {'ordering': "('name',)", 'object_name': 'EconomicResourceType'},
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'resource_types_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'resource_types_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['valueaccounting.EconomicResourceType']"}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'photo_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'rate': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '6', 'decimal_places': '2'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'unit': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'resource_units'", 'null': 'True', 'to': "orm['valueaccounting.Unit']"}),
            'unit_of_use': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'units_of_use'", 'null': 'True', 'to': "orm['valueaccounting.Unit']"}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'valueaccounting.eventtype': {
            'Meta': {'ordering': "('label',)", 'object_name': 'EventType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inverse_label': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'related_to': ('django.db.models.fields.CharField', [], {'default': "'process'", 'max_length': '12'}),
            'relationship': ('django.db.models.fields.CharField', [], {'default': "'in'", 'max_length': '12'}),
            'resource_effect': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'unit_type': ('django.db.models.fields.CharField', [], {'max_length': '12', 'blank': 'True'})
        },
        'valueaccounting.exchange': {
            'Meta': {'object_name': 'Exchange'},
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'exchanges_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'exchanges_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'process_pattern': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'exchanges'", 'null': 'True', 'to': "orm['valueaccounting.ProcessPattern']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'exchanges'", 'null': 'True', 'to': "orm['valueaccounting.Project']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'use_case': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'exchanges'", 'null': 'True', 'to': "orm['valueaccounting.UseCase']"})
        },
        'valueaccounting.facet': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Facet'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'})
        },
        'valueaccounting.facetvalue': {
            'Meta': {'ordering': "('facet', 'value')", 'unique_together': "(('facet', 'value'),)", 'object_name': 'FacetValue'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'facet': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'values'", 'to': "orm['valueaccounting.Facet']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'valueaccounting.feature': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Feature'},
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'features_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'features_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'event_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'features'", 'to': "orm['valueaccounting.EventType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'process_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'features'", 'null': 'True', 'to': "orm['valueaccounting.ProcessType']"}),
            'product': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'features'", 'to': "orm['valueaccounting.EconomicResourceType']"}),
            'quantity': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '8', 'decimal_places': '2'}),
            'unit_of_quantity': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'feature_units'", 'null': 'True', 'to': "orm['valueaccounting.Unit']"})
        },
        'valueaccounting.help': {
            'Meta': {'ordering': "('page',)", 'object_name': 'Help'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'page': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '16'})
        },
        'valueaccounting.option': {
            'Meta': {'ordering': "('component',)", 'object_name': 'Option'},
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'options_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'component': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'options'", 'to': "orm['valueaccounting.EconomicResourceType']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'options_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'feature': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'options'", 'to': "orm['valueaccounting.Feature']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'valueaccounting.order': {
            'Meta': {'ordering': "('due_date',)", 'object_name': 'Order'},
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'orders_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'orders_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'due_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'order_type': ('django.db.models.fields.CharField', [], {'default': "'customer'", 'max_length': '12'}),
            'provider': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'sales_orders'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'receiver': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'purchase_orders'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"})
        },
        'valueaccounting.patternfacetvalue': {
            'Meta': {'ordering': "('pattern', 'event_type', 'facet_value')", 'unique_together': "(('pattern', 'facet_value', 'event_type'),)", 'object_name': 'PatternFacetValue'},
            'event_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'patterns'", 'to': "orm['valueaccounting.EventType']"}),
            'facet_value': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'patterns'", 'to': "orm['valueaccounting.FacetValue']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pattern': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'facets'", 'to': "orm['valueaccounting.ProcessPattern']"})
        },
        'valueaccounting.patternusecase': {
            'Meta': {'object_name': 'PatternUseCase'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pattern': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'use_cases'", 'to': "orm['valueaccounting.ProcessPattern']"}),
            'use_case': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'patterns'", 'null': 'True', 'to': "orm['valueaccounting.UseCase']"})
        },
        'valueaccounting.process': {
            'Meta': {'ordering': "('end_date',)", 'object_name': 'Process'},
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'processes_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'processes_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'finished': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'managed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'managed_processes'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_processes'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'sub_processes'", 'null': 'True', 'to': "orm['valueaccounting.Process']"}),
            'process_pattern': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'processes'", 'null': 'True', 'to': "orm['valueaccounting.ProcessPattern']"}),
            'process_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'processes'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['valueaccounting.ProcessType']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'processes'", 'null': 'True', 'to': "orm['valueaccounting.Project']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'started': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'valueaccounting.processpattern': {
            'Meta': {'ordering': "('name',)", 'object_name': 'ProcessPattern'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'valueaccounting.processtype': {
            'Meta': {'ordering': "('name',)", 'object_name': 'ProcessType'},
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'process_types_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'process_types_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'estimated_duration': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'sub_process_types'", 'null': 'True', 'to': "orm['valueaccounting.ProcessType']"}),
            'process_pattern': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'process_types'", 'null': 'True', 'to': "orm['valueaccounting.ProcessPattern']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'process_types'", 'null': 'True', 'to': "orm['valueaccounting.Project']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'valueaccounting.processtyperesourcetype': {
            'Meta': {'ordering': "('resource_type',)", 'object_name': 'ProcessTypeResourceType'},
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'ptrts_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'ptrts_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'event_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'process_resource_types'", 'to': "orm['valueaccounting.EventType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'process_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resource_types'", 'to': "orm['valueaccounting.ProcessType']"}),
            'quantity': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '8', 'decimal_places': '2'}),
            'resource_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'process_types'", 'to': "orm['valueaccounting.EconomicResourceType']"}),
            'unit_of_quantity': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'process_resource_qty_units'", 'null': 'True', 'to': "orm['valueaccounting.Unit']"})
        },
        'valueaccounting.project': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Project'},
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'projects_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'projects_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'importance': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '3', 'decimal_places': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'sub_projects'", 'null': 'True', 'to': "orm['valueaccounting.Project']"}),
            'project_team': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'project_team'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'})
        },
        'valueaccounting.reciprocity': {
            'Meta': {'ordering': "('reciprocity_date',)", 'object_name': 'Reciprocity'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initiating_commitment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'initiated_commitments'", 'to': "orm['valueaccounting.Commitment']"}),
            'reciprocal_commitment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reciprocal_commitments'", 'to': "orm['valueaccounting.Commitment']"}),
            'reciprocity_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'})
        },
        'valueaccounting.resourcetypefacetvalue': {
            'Meta': {'ordering': "('resource_type', 'facet_value')", 'unique_together': "(('resource_type', 'facet_value'),)", 'object_name': 'ResourceTypeFacetValue'},
            'facet_value': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resource_types'", 'to': "orm['valueaccounting.FacetValue']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'facets'", 'to': "orm['valueaccounting.EconomicResourceType']"})
        },
        'valueaccounting.selectedoption': {
            'Meta': {'ordering': "('commitment', 'option')", 'object_name': 'SelectedOption'},
            'commitment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'options'", 'to': "orm['valueaccounting.Commitment']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'option': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'commitments'", 'to': "orm['valueaccounting.Option']"})
        },
        'valueaccounting.unit': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Unit'},
            'abbrev': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'symbol': ('django.db.models.fields.CharField', [], {'max_length': '1', 'blank': 'True'}),
            'unit_type': ('django.db.models.fields.CharField', [], {'max_length': '12'})
        },
        'valueaccounting.usecase': {
            'Meta': {'object_name': 'UseCase'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'restrict_to_one_pattern': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['valueaccounting']