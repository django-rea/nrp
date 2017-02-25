from django.contrib.auth.models import User, Group
from rest_framework import serializers

from django_rea.valueaccounting.models import *

class UserSerializer(serializers.HyperlinkedModelSerializer):
    api_url = serializers.HyperlinkedIdentityField(
        view_name='user-detail',
        lookup_field='pk'
    )
    class Meta:
        model = User
        fields = ('api_url', 'username', 'email',)

        
class UserCreationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password',)

        
class PlainContextSerializer(serializers.HyperlinkedModelSerializer):
    api_url = serializers.HyperlinkedIdentityField(
        view_name='context-detail',
        lookup_field='pk'
    )
    agent_type = serializers.RelatedField()
    class Meta:
        model = EconomicAgent
        fields = ('api_url', 'url', 'name', 'slug', 'agent_type', 'address',)

        
class EconomicAgentSerializer(serializers.HyperlinkedModelSerializer):
    api_url = serializers.HyperlinkedIdentityField(
        view_name='economicagent-detail',
        lookup_field='pk'
    )
    agent_type = serializers.RelatedField()
    projects = PlainContextSerializer(source='contexts_participated_in',
        many=True, read_only=True)
    class Meta:
        model = EconomicAgent
        fields = ('api_url', 'url', 'name', 'nick', 'slug', 'agent_type', 'address', 'email', 'projects')

        
class EconomicAgentCreationSerializer(serializers.HyperlinkedModelSerializer):
    #agent_type = serializers.RelatedField()
    class Meta:
        model = EconomicAgent
        fields = (
            'url', 
            'name', 
            'nick', 
            'agent_type', 
            'address', 
            'email',)
            
            
class AgentUserSerializer(serializers.HyperlinkedModelSerializer):
    api_url = serializers.HyperlinkedIdentityField(
        view_name='agentuser-detail',
        lookup_field='pk'
    )
    class Meta:
        model = AgentUser
        fields = ('api_url', 'agent', 'user')

        
class PeopleSerializer(serializers.HyperlinkedModelSerializer):
    #agent_type = serializers.RelatedField()
    api_url = serializers.HyperlinkedIdentityField(
        view_name='people-detail',
        lookup_field='pk'
    )
    projects = PlainContextSerializer(source='contexts_participated_in',
        many=True, read_only=True)
    class Meta:
        model = EconomicAgent
        fields = ('api_url', 'url', 'name', 'nick', 'agent_type', 'address', 'email', 'projects')
        
class PlainPeopleSerializer(serializers.HyperlinkedModelSerializer):
    #agent_type = serializers.RelatedField()
    api_url = serializers.HyperlinkedIdentityField(
        view_name='people-detail',
        lookup_field='pk'
    )
    class Meta:
        model = EconomicAgent
        fields = ('api_url', 'url', 'name', 'nick', 'agent_type', 'address', 'email',)
        
class ContextSerializer(serializers.HyperlinkedModelSerializer):
    api_url = serializers.HyperlinkedIdentityField(
        view_name='context-detail',
        lookup_field='pk'
    )
    agent_type = serializers.RelatedField()
    contributors = PlainPeopleSerializer(source='contributors',
        many=True, read_only=True)
    class Meta:
        model = EconomicAgent
        fields = ('api_url', 'url', 'name', 'slug', 'agent_type', 'address', 'contributors')
        
        
class AgentTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = AgentType
        fields = ('api_url', 'name', 'party_type', )
        
class EconomicEventSerializer(serializers.HyperlinkedModelSerializer):
    unit_of_quantity = serializers.RelatedField()
    class Meta:
        model = EconomicEvent
        fields = ('api_url', 
            'event_date', 
            'event_type', 
            'from_agent', 
            'to_agent',
            'context_agent',
            'resource_type',
            'resource',
            # todo: add process serializer to add process field here
            #'process',
            'description',
            'quantity',
            'unit_of_quantity',
            'is_contribution',
            )
        
class ContributionSerializer(serializers.HyperlinkedModelSerializer):
    unit_of_quantity = serializers.RelatedField()
    class Meta:
        model = EconomicEvent
        fields = ('api_url', 
            'event_date', 
            'event_type', 
            'from_agent', 
            'to_agent',
            'context_agent',
            'resource_type',
            'resource',
            # todo: add process serializer to add process field here
            #'process',
            'description',
            'quantity',
            'unit_of_quantity',
            'is_contribution',
            )

        
class EventTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = EventType
        fields = ('api_url', 'name', 'relationship', 'related_to', 'resource_effect',)
        
class ResourceTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = EconomicResourceType
        fields = ('api_url', 'name', )
        
class EconomicResourceSerializer(serializers.HyperlinkedModelSerializer):
    unit_of_quantity = serializers.Field(source='unit_of_quantity')
    class Meta:
        model = EconomicResource
        fields = ('api_url', 
            'resource_type', 
            'identifier',
            'notes',
            'quantity',
            'unit_of_quantity',)

class UnitSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Unit
        fields = ('api_url', 'unit_type', 'name', )
