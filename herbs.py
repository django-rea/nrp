import sys
import csv
from valuenetwork.valueaccounting.models import *

reader = csv.reader(open('herbs.csv', 'rb'))
import pdb; pdb.set_trace()
dry_parent = EconomicResourceType.objects.get(name="Herb - Dry")
pack_parent = EconomicResourceType.objects.get(name="Herb - Packaged")
lbs = Unit.objects.get(name="Pounds")
each = Unit.objects.get(name="Each")
fv = FacetValue.objects.get(value="Herb")

for row in reader:
    name = row[0]
   
    try:
        dry = EconomicResourceType (
            name=name,
            parent=dry_parent,
            unit=lbs,
            substitutable=True, 
            inventory_rule="yes",
        )
        dry.save()
        dry_fv = ResourceTypeFacetValue(
            resource_type=dry,
            facet_value=fv,
        )
        dry_fv.save()
        pack = EconomicResourceType (
            name=name + " 1 LB Package",
            parent=pack_parent,
            unit=each,
            substitutable=True, 
            inventory_rule="yes",
        )
        pack.save()
        pack_fv = ResourceTypeFacetValue(
            resource_type=pack,
            facet_value=fv,
        )
        pack_fv.save()
        print "herb: ", name
    except:
        print "Unexpected error:", sys.exc_info()[0]
