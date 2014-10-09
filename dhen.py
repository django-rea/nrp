import sys
import csv
from datetime import datetime
from decimal import *
from valuenetwork.valueaccounting.models import *

reader = csv.reader(open('dhen.csv', 'rb'))
#import pdb; pdb.set_trace()
ca = EconomicAgent.objects.get(nick="DHEN")
pt_dry = ProcessType.objects.get(name="Dry")
pt_harv = ProcessType.objects.get(name="Harvest")
lbs = Unit.objects.get(name="Pounds")
et_cc = EventType.objects.get(name="Create Changeable")
et_ch = EventType.objects.get(name="Change")
et_tbc = EventType.objects.get(name="To Be Changed")
owner_type = AgentResourceRoleType.objects.get(name="Owner")
dry_facility = EconomicAgent.objects.get(nick="Nam")
patt_create = ProcessPattern.objects.get(name="Create Changeable")
patt_change = ProcessPattern.objects.get(name="Change")

for row in reader:
    lot = row[0]
    month = int(lot[0])
    day = int(lot[1:3])
    year = 2014
    date_in = datetime.date(year, month, day)
    herb = row[1] 
    #import pdb; pdb.set_trace()
    herb_dry = EconomicResourceType.objects.get(name=herb)
    herb_pack = EconomicResourceType.objects.get(name=herb + " 1 LB Package")
    owners = []
    if row[3]:
        own = row[3].split("/")
        for nick in own:
            owners.append(EconomicAgent.objects.get(nick=nick))
    harvesters = []
    if row[4]:
        har = row[4].split("/")
        for h in har:
            harvesters.append(EconomicAgent.objects.get(nick=h))
    else:
        harvesters = owners
    if row[5]:
        farm = EconomicAgent.objects.get(nick=row[5])
    else:
        farm = None
    harv_notes = row[6]
    wet_wt = Decimal(row[7])
    dry_wt = None
    if row[8]:
        dry_wt = Decimal(row[8])
    dd = row[9] 
    date_dry = None
    if dd:
        month = int(dd[0])
        day = int(dd[1:3])
        year = 2014
        date_dry = datetime.date(year, month, day)
    notes = row[10]

    #import pdb; pdb.set_trace()
    try:
        harvest_proc = Process(
            name="Harvest " + herb,
            process_type=pt_harv,
            process_pattern=patt_create,
            context_agent=ca,
            start_date=date_in,
            end_date=date_in,
            finished=True,
        )
        harvest_proc.save()
        
        res = EconomicResource(
            resource_type=herb_dry,
            identifier=lot,
            stage=pt_dry,
            quantity=dry_wt,
            unit_of_quantity=lbs,
        )
        res.save()
        for owner in owners:
            res_owner = AgentResourceRole(
                agent=owner,
                resource=res,
                role=owner_type,
            )
            res_owner.save()
            
        for harv in harvesters:
            harvest_event = EconomicEvent(
                event_type=et_cc,
                event_date=date_in,
                from_agent=farm,
                to_agent=harv,
                resource_type=herb_dry,
                resource=res,
                process=harvest_proc,
                context_agent=ca,
                description=harv_notes,
                quantity=wet_wt / len(harvesters),
                unit_of_quantity=lbs,
                is_contribution=True,
            )
            harvest_event.save()
        
        if date_dry:
            dry_proc = Process(
                name="Dry " + herb,
                process_type=pt_dry,
                process_pattern=patt_change,
                context_agent=ca,
                start_date=date_in,
                end_date=date_dry,
                finished=True,
                notes=notes,
            )
            dry_proc.save()
            
            dry_event_in = EconomicEvent(
                event_type=et_tbc,
                event_date=date_in,
                from_agent=harvesters[0],
                to_agent=dry_facility,
                resource_type=herb_dry,
                resource=res,
                process=dry_proc,
                context_agent=ca,
                quantity=wet_wt,
                unit_of_quantity=lbs,
                is_contribution=False,
            )
            dry_event_in.save()
                    
            dry_event_out = EconomicEvent(
                event_type=et_ch,
                event_date=date_dry,
                from_agent=dry_facility,
                to_agent=dry_facility,
                resource_type=herb_dry,
                resource=res,
                process=dry_proc,
                context_agent=ca,
                description=notes,
                quantity=dry_wt,
                unit_of_quantity=lbs,
                is_contribution=True,
            )
            dry_event_out.save()
    
        print "lot: ", lot, "herb ", herb
    except:
        print "Unexpected error:" + lot, sys.exc_info()[0]
