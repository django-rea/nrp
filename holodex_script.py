"""
    Organization extractor.
    
    Puts AgentTypes, AgentAssociationTypes, AgentAssociations, and EconomicAgents
    into a single json file.
    This is very early work in process.
    For now, in the same directory where you do runserver, do
    python holodex_script.py
    Later on, it will become part of an API.
    It wants to evolve into producing whatever format Holodex wants.
"""
import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "valuenetwork.settings")

from django.utils import simplejson
from valuenetwork.valueaccounting.models import *

SCRIPT_ROOT = os.path.abspath(os.path.dirname(__file__))
file_path = os.path.join(SCRIPT_ROOT, "holodex", "dhen-data", "dhen.org")

agent_types = AgentType.objects.all()

at_dict = {}
for at in agent_types:
    fields = {
        "@type": "AgentType",
        "name": at.name,
        "is_context": at.is_context,
    }
    at_dict[at.name] = fields
    
agents = EconomicAgent.objects.all()
agent_dict = {}
for agent in agents:
    fields = {
        "@type": "EconomicAgent",
        "pk": agent.pk,
        "id": agent.nick,
        "name": agent.name,
        "agent_type": agent.agent_type.name,
    }
    agent_dict[agent.nick] = fields
    
aa_types = AgentAssociationType.objects.all()
aat_dict = {}
for aat in aa_types:
    fields = {
        "@type": "AgentAssociationType",
        "name": aat.name,
        "plural_name": aat.plural_name,
        "label": aat.label,
        "inverse_label": aat.inverse_label,
        "description": aat.description,
    }
    aat_dict[aat.name] = fields
    
associations = AgentAssociation.objects.all()
assoc_dict = {}
for a in associations:
    fields = {
        "@type": "AgentAssociation",
        "pk": a.pk,
        "source": a.is_associate.nick,
        "target": a.has_associate.nick,
        "association_type": a.association_type.name,
    }
    assoc_dict[a.pk] = fields
    
big_d = {
    "agentTypes": at_dict,
    "agents": agent_dict,
    "agentAssociationTypes": aat_dict,
    "agentAssociations": assoc_dict,
}

data = simplejson.dumps(big_d, indent=4)

f = open(file_path, "w")

f.write(data)

f.close()