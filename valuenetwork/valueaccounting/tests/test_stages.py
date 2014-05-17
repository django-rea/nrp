import datetime
from decimal import *

from django.test import TestCase
from django.test import Client

from valuenetwork.valueaccounting.models import *
from valuenetwork.valueaccounting.tests.objects_for_testing import *

class StageTest(TestCase):

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
        
        duration = 4320
        self.ideation = ProcessType(name="Ideation", estimated_duration=duration)
        self.ideation.save()
        self.curation = ProcessType(name="Curation", estimated_duration=duration)
        self.curation.save()
        self.finish = ProcessType(name="Finish", estimated_duration=duration)
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
        expected_stages = [
            self.ct1_create, 
            self.ct1_to_be, 
            self.ct2_change,
            self.ct2_to_be,
            self.ct3_change,
        ]
        process_types = sow.staged_process_type_sequence()
        expected_pts = [self.ideation, self.curation, self.finish]
        #import pdb; pdb.set_trace()
        self.assertEqual(stages, expected_stages)
        self.assertEqual(process_types, expected_pts)
        
    def test_staged_schedule(self):
        start = datetime.date.today()
        order = self.sow.generate_staged_work_order(start, self.user)
        #import pdb; pdb.set_trace()
        processes = order.all_processes()
        self.assertEqual(len(processes), 3)
        first = processes[0]
        second = processes[1]
        third = processes[2]
        self.assertEqual(first.start_date, start)
        next_start = start + datetime.timedelta(days=3)
        self.assertEqual(second.start_date, next_start)
        next_start = next_start + datetime.timedelta(days=3)
        self.assertEqual(third.start_date, next_start)
        due = next_start + datetime.timedelta(days=3)
        self.assertEqual(order.due_date, due)
        