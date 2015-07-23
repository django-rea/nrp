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

#agent_types = AgentType.objects.all()

#at_dict = OrderedDict()
#for at in agent_types:
#    fields = (
#        ("@type", "AgentType"),
#        ("name", at.name),
#        ("is_context", at.is_context),
#    )
#    fields = OrderedDict(fields)
#    at_dict[at.name] = fields
    
aa_types = AgentAssociationType.objects.all()
aat_dict = OrderedDict()
for aat in aa_types:
    label = aat.label.split(" ")[0]
    inverse = aat.inverse_label.split(" ")[0]
    id_r1 = "/".join(["roleTypes", label])
    id_r2 = "/".join(["roleTypes", inverse])
    id_l1 = "/".join(["linkTypes", aat.label.replace(' ', '-')])
    id_l2 = "/".join(["linkTypes", aat.inverse_label.replace(' ', '-')])
    id_rel_type = "/".join(["relationshipTypes", aat.name])
    role1 = (
        ("@type", "RoleType"),
        ("id", id_r1),
        ("name", label),
        ("pluralName", label + "s"),
        ("relationshipType", id_rel_type),
        ("linkType", id_l1),
        ("label", "role 1 label"),
    )
    role1 = OrderedDict(role1)
    role2 = (
        ("@type", "RoleType"),
        ("id", id_r2),
        ("name", inverse),
        ("pluralName", inverse + "s"),
        ("relationshipType", id_rel_type),
        ("linkType", id_l2),
        ("label", "role 2 label"),
    )
    role2 = OrderedDict(role2)
    roles = [role1, role2]
    link1 = (
        ("@type", "LinkType"),
        ("id", id_l1),
        ("relationshipType", id_rel_type),
        ("source", id_r1),
        ("target", id_r2),
        ("label", "link 1 label"),
    )
    link1 = OrderedDict(link1)
    link2 = (
        ("@type", "LinkType"),
        ("id", id_l2),
        ("relationshipType", id_rel_type),
        ("source", id_r2),
        ("target", id_r1),
        ("label", "link 2 label"),
    )
    link2 = OrderedDict(link2)
    links = [link1, link2]
    fields = (
        ("@type", "RelationshipType"),
        ("name", aat.name),
        ("pluralName", aat.plural_name),
        #("label", aat.label),
        #("inverse_label", aat.inverse_label),
        ("description", aat.description),
        ("roleTypes", roles),
        ("links", links),
    )
    fields = OrderedDict(fields)
    aat_dict[aat.name] = fields
    
associations = AgentAssociation.objects.all()
#assoc_dict = OrderedDict()
#for a in associations:
#    rel_type = "/".join(["relationshipTypes", a.association_type.name])
#    fields = (
#        ("@type", "Relationship"),
#        ("pk", a.pk),
#        ("source", a.is_associate.nick),
#        ("target", a.has_associate.nick),
#        ("type", rel_type),
#    )
#    fields = OrderedDict(fields)
#    assoc_dict[a.pk] = fields
    
agents = [assn.is_associate for assn in associations]
agents.extend([assn.has_associate for assn in associations])
agents = list(set(agents))

agent_dict = OrderedDict()
for agent in agents:
    if agent.agent_type.party_type == "individual":
        at_sub = "Person"
    else:
        at_sub = "Group"
    #agt_type = "/".join(["agentTypes", at_sub])
    relationships = []  
    agent_associations = list(agent.all_is_associates())
    agent_associations.extend(list(agent.all_has_associates()))
    for aa in agent_associations:
        rel_type = "relationshipTypes/" + aa.association_type.name
        if aa.is_associate.agent_type.party_type == "individual":
            dir = "people/"
        else:
            dir = "groups/"
        role1 = (
            ("@type", "Role"),
            ("type", "roleTypes/" + aa.association_type.label.split(" ")[0]),
            ("agent", dir + aa.is_associate.nick.replace(' ', '-')),
        )
        role1 = OrderedDict(role1)
        if aa.has_associate.agent_type.party_type == "individual":
            dir = "people/"
        else:
            dir = "groups/"
        role2 = (
            ("@type", "Role"),
            ("type", "roleTypes/" + aa.association_type.inverse_label.split(" ")[0]),
            ("agent", dir + aa.has_associate.nick.replace(' ', '-')),
        )
        role2 = OrderedDict(role2)
        roles = [role1, role2]
        rel = (
            ("@type", "Relationship"),
            ("type", rel_type),
            ("roles", roles),
        )
        rel = OrderedDict(rel)
        relationships.append(rel)
    fields = (
        ("@type", at_sub),
        #("pk", agent.pk),
        #("id", agent.nick),
        ("name", agent.name),
        #("type", agt_type),
        ("relationships", relationships),
    )
    fields = OrderedDict(fields)
    agent_dict[agent.nick] = fields
    
big_d = (
    #("agentTypes", at_dict),
    ("relationshipTypes", aat_dict),
    ("agents", agent_dict),
    #("relationships", assoc_dict),
)
big_d = OrderedDict(big_d)

data = simplejson.dumps(big_d, indent=4)

f = open(file_path, "w")

f.write(data)

f.close()