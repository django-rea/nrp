#import pdb; pdb.set_trace()
import sys
from django_rea.valueaccounting.models import *

agents = EconomicAgent.objects.all()

count = 0
for agent in agents:
    agent.is_context = agent.agent_type.is_context
    try:
        agent.save()
        count = count + 1
    except:
        print "Unexpected error:", sys.exc_info()[0]
        
print "count = " + str(count)
            

        
        

