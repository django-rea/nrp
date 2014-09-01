# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ClaimEvent'
        db.create_table('valueaccounting_claimevent', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(related_name='claim_events', to=orm['valueaccounting.EconomicEvent'])),
            ('claim', self.gf('django.db.models.fields.related.ForeignKey')(related_name='claims', to=orm['valueaccounting.Claim'])),
            ('claim_event_date', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
            ('value', self.gf('django.db.models.fields.DecimalField')(max_digits=8, decimal_places=2)),
            ('unit_of_value', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='claim_event_value_units', null=True, to=orm['valueaccounting.Unit'])),
            ('event_effect', self.gf('django.db.models.fields.CharField')(max_length=12)),
        ))
        db.send_create_signal('valueaccounting', ['ClaimEvent'])

        # Adding model 'ValueEquationBucketRule'
        db.create_table('valueaccounting_valueequationbucketrule', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('value_equation_bucket', self.gf('django.db.models.fields.related.ForeignKey')(related_name='bucket rules', to=orm['valueaccounting.ValueEquationBucket'])),
            ('event_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='value equation bucket rules', to=orm['valueaccounting.EventType'])),
            ('filter_rule', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('division_rule', self.gf('django.db.models.fields.CharField')(max_length=12)),
            ('claim_rule_type', self.gf('django.db.models.fields.CharField')(max_length=12)),
            ('claim_creation_equation', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='rules_created', null=True, to=orm['auth.User'])),
            ('changed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='rules_changed', null=True, to=orm['auth.User'])),
            ('created_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, null=True, blank=True)),
            ('changed_date', self.gf('django.db.models.fields.DateField')(auto_now=True, null=True, blank=True)),
        ))
        db.send_create_signal('valueaccounting', ['ValueEquationBucketRule'])

        # Adding model 'AgentValueEquation'
        db.create_table('valueaccounting_agentvalueequation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('context_agent', self.gf('django.db.models.fields.related.ForeignKey')(related_name='value_equations', to=orm['valueaccounting.EconomicAgent'])),
            ('value_equation', self.gf('django.db.models.fields.related.ForeignKey')(related_name='agents', to=orm['valueaccounting.ValueEquation'])),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='value_equations_assigned', null=True, to=orm['auth.User'])),
            ('created_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, null=True, blank=True)),
        ))
        db.send_create_signal('valueaccounting', ['AgentValueEquation'])

        # Adding model 'ValueEquation'
        db.create_table('valueaccounting_valueequation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='value_equations_created', null=True, to=orm['auth.User'])),
            ('created_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, null=True, blank=True)),
        ))
        db.send_create_signal('valueaccounting', ['ValueEquation'])

        # Adding model 'DistributionValueEquation'
        db.create_table('valueaccounting_distributionvalueequation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('distribution_date', self.gf('django.db.models.fields.DateField')()),
            ('exchange', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='value equation', null=True, to=orm['valueaccounting.Exchange'])),
            ('value_equation', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('valueaccounting', ['DistributionValueEquation'])

        # Adding model 'ValueEquationBucket'
        db.create_table('valueaccounting_valueequationbucket', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('sequence', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('value_equation', self.gf('django.db.models.fields.related.ForeignKey')(related_name='buckets', to=orm['valueaccounting.ValueEquation'])),
            ('percentage', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('distribution_agent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='value_equation_buckets', null=True, to=orm['valueaccounting.EconomicAgent'])),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='buckets_created', null=True, to=orm['auth.User'])),
            ('changed_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='buckets_changed', null=True, to=orm['auth.User'])),
            ('created_date', self.gf('django.db.models.fields.DateField')(auto_now_add=True, null=True, blank=True)),
            ('changed_date', self.gf('django.db.models.fields.DateField')(auto_now=True, null=True, blank=True)),
        ))
        db.send_create_signal('valueaccounting', ['ValueEquationBucket'])

        # Adding model 'Claim'
        db.create_table('valueaccounting_claim', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('claim_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='claims', to=orm['valueaccounting.EventType'])),
            ('claim_date', self.gf('django.db.models.fields.DateField')()),
            ('has_agent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='has_claims', null=True, to=orm['valueaccounting.EconomicAgent'])),
            ('against_agent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='claims against', null=True, to=orm['valueaccounting.EconomicAgent'])),
            ('context_agent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='claims', null=True, on_delete=models.SET_NULL, to=orm['valueaccounting.EconomicAgent'])),
            ('value', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=8, decimal_places=2)),
            ('unit_of_value', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='claim_value_units', null=True, to=orm['valueaccounting.Unit'])),
            ('claim_creation_equation', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
        ))
        db.send_create_signal('valueaccounting', ['Claim'])


    def backwards(self, orm):
        # Deleting model 'ClaimEvent'
        db.delete_table('valueaccounting_claimevent')

        # Deleting model 'ValueEquationBucketRule'
        db.delete_table('valueaccounting_valueequationbucketrule')

        # Deleting model 'AgentValueEquation'
        db.delete_table('valueaccounting_agentvalueequation')

        # Deleting model 'ValueEquation'
        db.delete_table('valueaccounting_valueequation')

        # Deleting model 'DistributionValueEquation'
        db.delete_table('valueaccounting_distributionvalueequation')

        # Deleting model 'ValueEquationBucket'
        db.delete_table('valueaccounting_valueequationbucket')

        # Deleting model 'Claim'
        db.delete_table('valueaccounting_claim')


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
        'valueaccounting.accountingreference': {
            'Meta': {'object_name': 'AccountingReference'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'valueaccounting.agentassociation': {
            'Meta': {'ordering': "('is_associate',)", 'object_name': 'AgentAssociation'},
            'association_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'associations'", 'to': "orm['valueaccounting.AgentAssociationType']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'has_associate': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'has_associates'", 'to': "orm['valueaccounting.EconomicAgent']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_associate': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'is_associate_of'", 'to': "orm['valueaccounting.EconomicAgent']"}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'active'", 'max_length': '12'})
        },
        'valueaccounting.agentassociationtype': {
            'Meta': {'object_name': 'AgentAssociationType'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '12'}),
            'inverse_label': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'plural_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'})
        },
        'valueaccounting.agentresourcerole': {
            'Meta': {'object_name': 'AgentResourceRole'},
            'agent': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'agent_resource_roles'", 'to': "orm['valueaccounting.EconomicAgent']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_contact': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'owner_percentage': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'agent_resource_roles'", 'to': "orm['valueaccounting.EconomicResource']"}),
            'role': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'agent_resource_roles'", 'to': "orm['valueaccounting.AgentResourceRoleType']"})
        },
        'valueaccounting.agentresourceroletype': {
            'Meta': {'object_name': 'AgentResourceRoleType'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_owner': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
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
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_context': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
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
        'valueaccounting.agentvalueequation': {
            'Meta': {'object_name': 'AgentValueEquation'},
            'context_agent': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'value_equations'", 'to': "orm['valueaccounting.EconomicAgent']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'value_equations_assigned'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value_equation': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'agents'", 'to': "orm['valueaccounting.ValueEquation']"})
        },
        'valueaccounting.cachedeventsummary': {
            'Meta': {'ordering': "('agent', 'context_agent', 'resource_type')", 'object_name': 'CachedEventSummary'},
            'agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'cached_events'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'context_agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'context_cached_events'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'event_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cached_events'", 'to': "orm['valueaccounting.EventType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'importance': ('django.db.models.fields.DecimalField', [], {'default': "'1'", 'max_digits': '3', 'decimal_places': '0'}),
            'quantity': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '8', 'decimal_places': '2'}),
            'reputation': ('django.db.models.fields.DecimalField', [], {'default': "'1.00'", 'max_digits': '8', 'decimal_places': '2'}),
            'resource_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'cached_events'", 'null': 'True', 'to': "orm['valueaccounting.EconomicResourceType']"}),
            'resource_type_rate': ('django.db.models.fields.DecimalField', [], {'default': "'1.0'", 'max_digits': '8', 'decimal_places': '2'}),
            'value': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '8', 'decimal_places': '2'})
        },
        'valueaccounting.claim': {
            'Meta': {'ordering': "('-claim_date',)", 'object_name': 'Claim'},
            'against_agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'claims against'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'claim_creation_equation': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'claim_date': ('django.db.models.fields.DateField', [], {}),
            'claim_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'claims'", 'to': "orm['valueaccounting.EventType']"}),
            'context_agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'claims'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'has_agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'has_claims'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'unit_of_value': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'claim_value_units'", 'null': 'True', 'to': "orm['valueaccounting.Unit']"}),
            'value': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '8', 'decimal_places': '2'})
        },
        'valueaccounting.claimevent': {
            'Meta': {'ordering': "('claim_event_date',)", 'object_name': 'ClaimEvent'},
            'claim': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'claims'", 'to': "orm['valueaccounting.Claim']"}),
            'claim_event_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'claim_events'", 'to': "orm['valueaccounting.EconomicEvent']"}),
            'event_effect': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'unit_of_value': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'claim_event_value_units'", 'null': 'True', 'to': "orm['valueaccounting.Unit']"}),
            'value': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'})
        },
        'valueaccounting.commitment': {
            'Meta': {'ordering': "('due_date',)", 'object_name': 'Commitment'},
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitments_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'commitment_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'context_agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitments'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
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
            'order_item': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'stream_commitments'", 'null': 'True', 'to': "orm['valueaccounting.Commitment']"}),
            'process': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitments'", 'null': 'True', 'to': "orm['valueaccounting.Process']"}),
            'quality': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '3', 'decimal_places': '0'}),
            'quantity': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '2'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitments'", 'null': 'True', 'to': "orm['valueaccounting.EconomicResource']"}),
            'resource_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitments'", 'null': 'True', 'to': "orm['valueaccounting.EconomicResourceType']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'stage': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitments_at_stage'", 'null': 'True', 'to': "orm['valueaccounting.ProcessType']"}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitments_at_state'", 'null': 'True', 'to': "orm['valueaccounting.ResourceState']"}),
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
        'valueaccounting.distributionvalueequation': {
            'Meta': {'object_name': 'DistributionValueEquation'},
            'distribution_date': ('django.db.models.fields.DateField', [], {}),
            'exchange': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'value equation'", 'null': 'True', 'to': "orm['valueaccounting.Exchange']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value_equation': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
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
            'context_agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'event_date': ('django.db.models.fields.DateField', [], {}),
            'event_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'events'", 'to': "orm['valueaccounting.EventType']"}),
            'exchange': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['valueaccounting.Exchange']"}),
            'from_agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'given_events'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_contribution': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'process': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['valueaccounting.Process']"}),
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
            'access_rules': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'authored_resources'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'resources_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'resources_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'current_location': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'resources_at_location'", 'null': 'True', 'to': "orm['valueaccounting.Location']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'independent_demand': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'dependent_resources'", 'null': 'True', 'to': "orm['valueaccounting.Order']"}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'order_item': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'stream_resources'", 'null': 'True', 'to': "orm['valueaccounting.Commitment']"}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'photo_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'quality': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'null': 'True', 'max_digits': '3', 'decimal_places': '0', 'blank': 'True'}),
            'quantity': ('django.db.models.fields.DecimalField', [], {'default': "'1.00'", 'max_digits': '8', 'decimal_places': '2'}),
            'resource_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': "orm['valueaccounting.EconomicResourceType']"}),
            'stage': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'resources_at_stage'", 'null': 'True', 'to': "orm['valueaccounting.ProcessType']"}),
            'state': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'resources_at_state'", 'null': 'True', 'to': "orm['valueaccounting.ResourceState']"}),
            'unit_of_quantity': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'resource_qty_units'", 'null': 'True', 'to': "orm['valueaccounting.Unit']"}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'valueaccounting.economicresourcetype': {
            'Meta': {'ordering': "('name',)", 'object_name': 'EconomicResourceType'},
            'accounting_reference': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'resource_types'", 'null': 'True', 'to': "orm['valueaccounting.AccountingReference']"}),
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'resource_types_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'resource_types_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inventory_rule': ('django.db.models.fields.CharField', [], {'default': "'yes'", 'max_length': '5'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['valueaccounting.EconomicResourceType']"}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'photo_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'rate': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '6', 'decimal_places': '2'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'substitutable': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
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
            'Meta': {'ordering': "('-start_date',)", 'object_name': 'Exchange'},
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'exchanges_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'context_agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'exchanges'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'exchanges_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'exchanges_as_customer'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'order': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'cash_receipts'", 'null': 'True', 'to': "orm['valueaccounting.Order']"}),
            'process_pattern': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'exchanges'", 'null': 'True', 'to': "orm['valueaccounting.ProcessPattern']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'supplier': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'exchanges_as_supplier'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
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
        'valueaccounting.homepagelayout': {
            'Meta': {'object_name': 'HomePageLayout'},
            'banner': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'creations_panel_headline': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'footer': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'needs_panel_headline': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'panel_1': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'panel_2': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'panel_3': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'use_creations_panel': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'use_needs_panel': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'use_work_panel': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'work_panel_headline': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'valueaccounting.location': {
            'Meta': {'object_name': 'Location'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latitude': ('django.db.models.fields.FloatField', [], {'default': '0.0', 'null': 'True', 'blank': 'True'}),
            'longitude': ('django.db.models.fields.FloatField', [], {'default': '0.0', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
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
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
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
            'Meta': {'ordering': "('-end_date',)", 'object_name': 'Process'},
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'processes_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'context_agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'processes'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'processes_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'finished': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'sub_processes'", 'null': 'True', 'to': "orm['valueaccounting.Process']"}),
            'process_pattern': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'processes'", 'null': 'True', 'to': "orm['valueaccounting.ProcessPattern']"}),
            'process_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'processes'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['valueaccounting.ProcessType']"}),
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
            'context_agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'process_types'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'process_types_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'estimated_duration': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'sub_process_types'", 'null': 'True', 'to': "orm['valueaccounting.ProcessType']"}),
            'process_pattern': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'process_types'", 'null': 'True', 'to': "orm['valueaccounting.ProcessPattern']"}),
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
            'stage': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitmenttypes_at_stage'", 'null': 'True', 'to': "orm['valueaccounting.ProcessType']"}),
            'state': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'commitmenttypes_at_state'", 'null': 'True', 'to': "orm['valueaccounting.ResourceState']"}),
            'unit_of_quantity': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'process_resource_qty_units'", 'null': 'True', 'to': "orm['valueaccounting.Unit']"})
        },
        'valueaccounting.reciprocity': {
            'Meta': {'ordering': "('reciprocity_date',)", 'object_name': 'Reciprocity'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initiating_commitment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'initiated_commitments'", 'to': "orm['valueaccounting.Commitment']"}),
            'reciprocal_commitment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reciprocal_commitments'", 'to': "orm['valueaccounting.Commitment']"}),
            'reciprocity_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'})
        },
        'valueaccounting.resourcestate': {
            'Meta': {'object_name': 'ResourceState'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        'valueaccounting.resourcetypefacetvalue': {
            'Meta': {'ordering': "('resource_type', 'facet_value')", 'unique_together': "(('resource_type', 'facet_value'),)", 'object_name': 'ResourceTypeFacetValue'},
            'facet_value': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resource_types'", 'to': "orm['valueaccounting.FacetValue']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'facets'", 'to': "orm['valueaccounting.EconomicResourceType']"})
        },
        'valueaccounting.resourcetypelist': {
            'Meta': {'ordering': "('name',)", 'object_name': 'ResourceTypeList'},
            'context_agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'lists'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'valueaccounting.resourcetypelistelement': {
            'Meta': {'ordering': "('resource_type_list', 'resource_type')", 'unique_together': "(('resource_type_list', 'resource_type'),)", 'object_name': 'ResourceTypeListElement'},
            'default_quantity': ('django.db.models.fields.DecimalField', [], {'default': "'1.0'", 'max_digits': '8', 'decimal_places': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'lists'", 'to': "orm['valueaccounting.EconomicResourceType']"}),
            'resource_type_list': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'list_elements'", 'to': "orm['valueaccounting.ResourceTypeList']"})
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
        },
        'valueaccounting.usecaseeventtype': {
            'Meta': {'object_name': 'UseCaseEventType'},
            'event_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'use_cases'", 'to': "orm['valueaccounting.EventType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'use_case': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'event_types'", 'to': "orm['valueaccounting.UseCase']"})
        },
        'valueaccounting.valueequation': {
            'Meta': {'object_name': 'ValueEquation'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'value_equations_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'valueaccounting.valueequationbucket': {
            'Meta': {'object_name': 'ValueEquationBucket'},
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'buckets_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'buckets_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'distribution_agent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'value_equation_buckets'", 'null': 'True', 'to': "orm['valueaccounting.EconomicAgent']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'percentage': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'sequence': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'value_equation': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'buckets'", 'to': "orm['valueaccounting.ValueEquation']"})
        },
        'valueaccounting.valueequationbucketrule': {
            'Meta': {'object_name': 'ValueEquationBucketRule'},
            'changed_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'rules_changed'", 'null': 'True', 'to': "orm['auth.User']"}),
            'changed_date': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'claim_creation_equation': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'claim_rule_type': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'rules_created'", 'null': 'True', 'to': "orm['auth.User']"}),
            'created_date': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'division_rule': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'event_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'value equation bucket rules'", 'to': "orm['valueaccounting.EventType']"}),
            'filter_rule': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'value_equation_bucket': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bucket rules'", 'to': "orm['valueaccounting.ValueEquationBucket']"})
        }
    }

    complete_apps = ['valueaccounting']