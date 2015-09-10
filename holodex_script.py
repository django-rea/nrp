"""
    Organization extractor.
    
    Puts AgentTypes, AgentAssociationTypes, AgentAssociations, and EconomicAgents
    into csv files.
    This is very early work in process.
    For now, in the same directory where you do runserver, do
    python holodex_script.py
    Later on, it will become part of an API.
    It wants to evolve into producing whatever format Holodex wants.
"""
import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "valuenetwork.settings")

#from collections import OrderedDict

#from django.utils import simplejson
import csv

from valuenetwork.valueaccounting.models import *

SCRIPT_ROOT = os.path.abspath(os.path.dirname(__file__))
#file_path = os.path.join(SCRIPT_ROOT, "holodex", "dhen-data", "org.json")
at_file_path = os.path.join(SCRIPT_ROOT, "holodex", "dhen-data", "agentTypes.csv")
aat_file_path = os.path.join(SCRIPT_ROOT, "holodex", "dhen-data", "relationshipTypes.csv")
a_file_path = os.path.join(SCRIPT_ROOT, "holodex", "dhen-data", "agents.csv")
aa_file_path = os.path.join(SCRIPT_ROOT, "holodex", "dhen-data", "agentRelationships.csv")

#import pdb; pdb.set_trace()
agent_types = AgentType.objects.all()
with open(at_file_path, 'wb') as csvfile:
    w = csv.writer(csvfile, delimiter=',', quotechar="'", quoting=csv.QUOTE_ALL)
    for at in agent_types:
        id = "http://dhen.webfactional.com/admin/valueaccounting/agenttype/" + str(at.id) + "/"        
        name = at.name
        description = at.description
        #is_context = at.is_context
        w.writerow([id, name, description])
    
aa_types = AgentAssociationType.objects.all()
with open(aat_file_path, 'wb') as csvfile:
    w = csv.writer(csvfile, delimiter=',', quotechar="'", quoting=csv.QUOTE_ALL)
    for aat in aa_types:
        id = "http://dhen.webfactional.com/admin/valueaccounting/relationshiptype/" + str(aat.id) + "/" 
        
        label = aat.label.split(" ")[0]
        inverse = aat.inverse_label.split(" ")[0]
        id_r1 = "/".join(["roleTypes", label])
        id_r2 = "/".join(["roleTypes", inverse])
        id_l1 = "/".join(["linkTypes", aat.label.replace(' ', '-')])
        id_l2 = "/".join(["linkTypes", aat.inverse_label.replace(' ', '-')])
        id_rel_type = "/".join(["relationshipTypes", aat.name])

        name = aat.name
        pluralName = aat.plural_name
        #("label", aat.label),
        #("inverse_label", aat.inverse_label),
        description = aat.description

        w.writerow([id, name, pluraName, description])
    
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

with open(a_file_path, 'wb') as csvfile:
    w = csv.writer(csvfile, delimiter=',', quotechar="'", quoting=csv.QUOTE_ALL)
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
            
            
        
        #("pk", agent.pk),
        #("id", agent.nick),
        name = agent.name
        type = agt_type.
        ("relationships", relationships),

        w.writerow([id, name, ])
    




'''
import csv
with open('eggs.csv', 'wb') as csvfile:
    spamwriter = csv.writer(csvfile, delimiter=' ',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
    spamwriter.writerow(['Spam'] * 5 + ['Baked Beans'])
    spamwriter.writerow(['Spam', 'Lovely Spam', 'Wonderful Spam'])
    
with open('some.csv', 'wb') as f:
    writer = csv.writer(f)
    writer.writerows(someiterable)
    
The csv module defines the following exception:

exception csv.Error

    Raised by any of the functions when an error is detected.


def exchange_events_csv(request):
    #import pdb; pdb.set_trace()
    event_ids = request.GET.get("event-ids")
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=contributions.csv'
    writer = csv.writer(response)
    writer.writerow(["Date", "Event Type", "Resource Type", "Quantity", "Unit of Quantity", "Value", "Unit of Value", "From Agent", "To Agent", "Project", "Description", "URL", "Use Case", "Event ID", "Exchange ID"])
    event_ids_split = event_ids.split(",")
    for event_id in event_ids_split:
        event = EconomicEvent.objects.get(pk=event_id)
        if event.from_agent == None:
            from_agent = ""
        else:
            from_agent = event.from_agent.nick
        if event.to_agent == None:
            to_agent = ""
        else:
            to_agent = event.to_agent.nick  
        if event.url == "":
            if event.exchange.url == "":
                url = "" 
            else:
                url = event.exchange.url
        else:
            url = ""     
        writer.writerow(
            [event.event_date,
             event.event_type.name,
             event.resource_type.name,
             event.quantity,
             event.unit_of_quantity,
             event.value,
             event.unit_of_value,
             from_agent,
             to_agent,
             event.context_agent.name,
             event.description,
             url,
             event.exchange.use_case,
             event.id,
             event.exchange.id   
            ]
        )
    return response
'''