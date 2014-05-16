import datetime
from decimal import *

from django.test import TestCase
from django.test import Client

from valuenetwork.valueaccounting.models import *
from valuenetwork.valueaccounting.tests.objects_for_testing import *

class ExplosionTest(TestCase):

    """Testing stages (changeable resources)
    """

    def setUp(self):

        self.user = User.objects.create_user('alice', 'alice@whatever.com', 'password')
        
        self.creation_et = EventType.objects.get(name='Create Changeable') 
        self.to_be_et = EventType.objects.get(name='To Be Changed')
        self.change_et = EventType.objects.get(name='Change')
        
        self.sow = EconomicResourceType(
            name="Pre_SOW",
            substitutable=False)
        self.sow.save()
        
        self.ideation = ProcessType(name="Ideation")
        self.ideation.save()
        self.curation = ProcessType(name="Curation")
        self.curation.save()
        self.finish = ProcessType(name="Finish")
        self.finish.save()
        
        qty = Decimal("1.0")
        
        self.ct1_create = ProcessTypeResourceType(
            process_type=self.ideation,
            resource_type=self.sow,
            event_type=self.creation_et,
            stage=self.ideation,
            quantity=qty,
        )
        self.ct1_create.save()
        
        self.ct1_to_be = ProcessTypeResourceType(
            process_type=self.curation,
            resource_type=self.sow,
            event_type=self.to_be_et,
            stage=self.ideation,
            quantity=qty,
        )
        self.ct1_to_be.save()
        
        self.ct2_change = ProcessTypeResourceType(
            process_type=self.curation,
            resource_type=self.sow,
            event_type=self.change_et,
            stage=self.curation,
            quantity=qty,
        )
        self.ct2_change.save()
        
        self.ct2_to_be = ProcessTypeResourceType(
            process_type=self.finish,
            resource_type=self.sow,
            event_type=self.to_be_et,
            stage=self.curation,
            quantity=qty,
        )
        self.ct2_to_be.save()
        
        self.ct3_change = ProcessTypeResourceType(
            process_type=self.finish,
            resource_type=self.sow,
            event_type=self.change_et,
            stage=self.finish,
            quantity=qty,
        )
        self.ct3_change.save()
        
        
    def test_stage_sequence(self):
        sow = self.sow
        cts = sow.process_types.all()
        ct4 = cts[4]
        pt = ct4.process_type
        stages = sow.staged_commitment_type_sequence()
        process_types = sow.staged_process_type_sequence()
        import pdb; pdb.set_trace()
        
        