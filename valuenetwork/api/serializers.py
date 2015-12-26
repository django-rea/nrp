from django.contrib.auth.models import User, Group
from rest_framework import serializers

from valuenetwork.valueaccounting.models import *

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('api_url', 'username', 'email', 'groups')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('api_url', 'name')
        
class EconomicAgentSerializer(serializers.HyperlinkedModelSerializer):
    agent_type = serializers.RelatedField()
    projects = serializers.Field(source='contexts_participated_in')
    class Meta:
        model = EconomicAgent
        fields = ('api_url', 'url', 'name', 'nick', 'slug', 'agent_type', 'address', 'email', 'projects')
        
class ContextSerializer(serializers.HyperlinkedModelSerializer):
    agent_type = serializers.RelatedField()
    class Meta:
        model = EconomicAgent
        fields = ('api_url', 'url', 'name', 'slug', 'agent_type', 'address',)
        
        
class AgentTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = AgentType
        fields = ('api_url', 'name', 'party_type', )

class PeopleSerializer(serializers.HyperlinkedModelSerializer):
    agent_type = serializers.RelatedField()
    projects = ContextSerializer(source='contexts_participated_in', many=True)
    class Meta:
        model = EconomicAgent
        fields = ('api_url', 'url', 'name', 'nick', 'agent_type', 'address', 'email', 'projects')
        
class EconomicEventSerializer(serializers.HyperlinkedModelSerializer):
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
    class Meta:
        model = EconomicResource
        fields = ('api_url', 
            'resource_type', 
            'identifier',
            'description',
            'quantity',
            'unit_of_quantity',)

class UnitSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Unit
        fields = ('api_url', 'unit_type', 'name', )
