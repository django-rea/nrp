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

from collections import OrderedDict

from django.utils import simplejson

from valuenetwork.valueaccounting.models import *

SCRIPT_ROOT = os.path.abspath(os.path.dirname(__file__))
file_path = os.path.join(SCRIPT_ROOT, "holodex", "dhen-data", "org.json")

agent_types = AgentType.objects.all()

at_dict = OrderedDict()
for at in agent_types:
    fields = (
        ("@type", "AgentType"),
        ("name", at.name),
        ("is_context", at.is_context),
    )
    fields = OrderedDict(fields)
    at_dict[at.name] = fields
    
aa_types = AgentAssociationType.objects.all()
aat_dict = OrderedDict()
for aat in aa_types:
    label = aat.label.split(" ")[0]
    inverse = aat.inverse_label.split(" ")[0]
    id = "/".join(["roleTypes", label])
    rel_type = "/".join(["relationshipTypes", aat.name])
    role1 = (
        ("@type", "RoleType"),
        ("id", id),
        ("name", label),
        ("pluralName", label + "s"),
        ("relationshipType", rel_type),
        ("linkType", "whatever"),
        ("label", "whatever"),
    )
    role1 = OrderedDict(role1)
    role2 = (
        ("@type", "RoleType"),
        ("id", id),
        ("name", inverse),
        ("pluralName", inverse + "s"),
        ("relationshipType", rel_type),
        ("linkType", "whatever"),
        ("label", "whatever"),
    )
    role2 = OrderedDict(role2)
    roles = [role1, role2]
    fields = (
        ("@type", "RelationshipType"),
        ("name", aat.name),
        ("plural_name", aat.plural_name),
        ("label", aat.label),
        ("inverse_label", aat.inverse_label),
        ("description", aat.description),
        ("roleTypes", roles),
    )
    fields = OrderedDict(fields)
    aat_dict[aat.name] = fields
    
associations = AgentAssociation.objects.all()
assoc_dict = OrderedDict()
for a in associations:
    rel_type = "/".join(["relationshipTypes", a.association_type.name])
    fields = (
        ("@type", "Relationship"),
        ("pk", a.pk),
        ("source", a.is_associate.nick),
        ("target", a.has_associate.nick),
        ("type", rel_type),
    )
    fields = OrderedDict(fields)
    assoc_dict[a.pk] = fields
    
agents = [assn.is_associate for assn in associations]
agents.extend([assn.has_associate for assn in associations])
agents = list(set(agents))

agent_dict = OrderedDict()
for agent in agents:
    agt_type = "/".join(["agentTypes", agent.agent_type.name])
    fields = (
        ("@type", "Agent"),
        ("pk", agent.pk),
        ("id", agent.nick),
        ("name", agent.name),
        ("type", agt_type),
    )
    fields = OrderedDict(fields)
    agent_dict[agent.nick] = fields
    
big_d = (
    ("agentTypes", at_dict),
    ("relationshipTypes", aat_dict),
    ("agents", agent_dict),
    ("relationships", assoc_dict),
)
big_d = OrderedDict(big_d)

data = simplejson.dumps(big_d, indent=4)

f = open(file_path, "w")

f.write(data)

f.close()