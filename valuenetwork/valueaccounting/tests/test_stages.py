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
        self.work_et = EventType.objects.get(relationship='work')
        
        # create_changeable recipe
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
        
        #resource_driven recipe
        self.equip = EconomicResourceType(
            name="Equipment",
            substitutable=False)
        self.equip.save()
        
        self.work = EconomicResourceType(
            name="Repair work",)
        self.work.save()
        
        duration = 4320
        self.diagnose = ProcessType(name="Diagnose", estimated_duration=duration)
        self.diagnose.save()
        self.repair = ProcessType(name="Repair", estimated_duration=duration)
        self.repair.save()
        self.test = ProcessType(name="Test", estimated_duration=duration)
        self.test.save()
        
        qty = Decimal("1.0")
        
        self.rd1_to_be = ProcessTypeResourceType(
            process_type=self.diagnose,
            resource_type=self.equip,
            event_type=self.to_be_et,
            stage=None,
            quantity=qty,
        )
        self.rd1_to_be.save()
        
        self.rd1_diagnose = ProcessTypeResourceType(
            process_type=self.diagnose,
            resource_type=self.equip,
            event_type=self.change_et,
            stage=self.diagnose,
            quantity=qty,
        )
        self.rd1_diagnose.save()
                      
        self.rd2_to_be = ProcessTypeResourceType(
            process_type=self.repair,
            resource_type=self.equip,
            event_type=self.to_be_et,
            stage=self.diagnose,
            quantity=qty,
        )
        self.rd2_to_be.save()
        
        self.rd2_work = ProcessTypeResourceType(
            process_type=self.repair,
            resource_type=self.work,
            event_type=self.work_et,
            quantity=qty,
        )
        self.rd2_work.save()
        
        self.rd2_repair = ProcessTypeResourceType(
            process_type=self.repair,
            resource_type=self.equip,
            event_type=self.change_et,
            stage=self.repair,
            quantity=qty,
        )
        self.rd2_repair.save()
        
        self.rd3_to_be = ProcessTypeResourceType(
            process_type=self.test,
            resource_type=self.equip,
            event_type=self.to_be_et,
            stage=self.repair,
            quantity=qty,
        )
        self.rd3_to_be.save()
        
        self.rd3_test = ProcessTypeResourceType(
            process_type=self.test,
            resource_type=self.equip,
            event_type=self.change_et,
            stage=self.test,
            quantity=qty,
        )
        self.rd3_test.save()
        
        
    def test_stage_sequence(self):
        sow = self.sow
        cts = sow.process_types.all()
        ct4 = cts[4]
        pt = ct4.process_type
        stages, inheritance = sow.staged_commitment_type_sequence()
        expected_stages = [
            self.ct1_create, 
            self.ct1_to_be, 
            self.ct2_change,
            self.ct2_to_be,
            self.ct3_change,
        ]
        process_types, inheritance = sow.staged_process_type_sequence()
        expected_pts = [self.ideation, self.curation, self.finish]
        #import pdb; pdb.set_trace()
        self.assertEqual(stages, expected_stages)
        self.assertEqual(process_types, expected_pts)
        
    def test_staged_schedule(self):
        start = datetime.date.today()
        order = self.sow.generate_staged_work_order("test order", start, self.user)
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
        
    def test_staged_explosion(self):
        """ stages allow the same resource type to re-occur in an explosion
        
            if the occurrences have different stages.
        """
        due_date = datetime.date.today()
        commitment = self.ct3_change.create_commitment(due_date, self.user)
        visited = []
        #import pdb; pdb.set_trace()
        process = commitment.generate_producing_process(self.user, visited, explode=True)
        prev = process.previous_processes()[0]
        prev_prev = prev.previous_processes()[0]
        process_start = due_date - datetime.timedelta(days=3)
        self.assertEqual(process.start_date, process_start)
        prev_start = due_date - datetime.timedelta(days=6)
        self.assertEqual(prev.start_date, prev_start)
        prev_prev_start = due_date - datetime.timedelta(days=9)
        self.assertEqual(prev_prev.start_date, prev_prev_start)
        ordered_processes = []
        visited_resources = []
        all_prevs = process.all_previous_processes(ordered_processes, visited_resources, 0)
        self.assertEqual(len(ordered_processes), 3)
        prev_next = prev.next_processes()[0]
        self.assertEqual(prev_next, process)
        prev_prev_next = prev_prev.next_processes()[0]
        self.assertEqual(prev_prev_next, prev)
        #import pdb; pdb.set_trace()
        
    def test_staged_schedule_using_inherited_recipe(self):
        heir = EconomicResourceType(
            name="heir",
            parent=self.sow,
        )
        heir.save()
        start = datetime.date.today()
        order = heir.generate_staged_work_order("test order", start, self.user)
        #import pdb; pdb.set_trace()
        #todo pr: all commitments use parent, not heir
        processes = order.all_processes()
        self.assertEqual(len(processes), 3)
        for process in processes:
            rt = process.output_resource_types()[0]
            self.assertEqual(rt, heir)

        
    def test_staged_explosion_using_inherited_recipe(self):
        """ stages allow the same resource type to re-occur in an explosion
        
            if the occurrences have different stages.
        """
        heir = EconomicResourceType(
            name="heir",
            parent=self.sow,
        )
        heir.save()
        due_date = datetime.date.today()
        commitment = self.ct3_change.create_commitment(due_date, self.user)
        visited = []
        #import pdb; pdb.set_trace()
        process = commitment.generate_producing_process(self.user, visited, explode=True)
        prev = process.previous_processes()[0]
        prev_prev = prev.previous_processes()[0]
        process_start = due_date - datetime.timedelta(days=3)
        self.assertEqual(process.start_date, process_start)
        prev_start = due_date - datetime.timedelta(days=6)
        self.assertEqual(prev.start_date, prev_start)
        prev_prev_start = due_date - datetime.timedelta(days=9)
        self.assertEqual(prev_prev.start_date, prev_prev_start)
        ordered_processes = []
        visited_resources = []
        all_prevs = process.all_previous_processes(ordered_processes, visited_resources, 0)
        self.assertEqual(len(ordered_processes), 3)
        prev_next = prev.next_processes()[0]
        self.assertEqual(prev_next, process)
        prev_prev_next = prev_prev.next_processes()[0]
        self.assertEqual(prev_prev_next, prev)
        #import pdb; pdb.set_trace()
          
    def test_resource_driven_order(self):
        repair_me = EconomicResource(
            resource_type = self.equip,
            identifier = "Test",
            quantity = Decimal("1.0")
        )
        repair_me.save()
        start = datetime.date.today()
        #import pdb; pdb.set_trace()
        order = self.equip.generate_staged_work_order_from_resource(repair_me, "Test repair", start, self.user)
        self.assertEqual(len(order.all_processes()), 3)
        #import pdb; pdb.set_trace()
             
    def test_resource_driven_order_using_inherited_recipe(self):
        heir = EconomicResourceType(
            name="heir",
            parent=self.equip,
        )
        heir.save()
        repair_me = EconomicResource(
            resource_type = heir,
            identifier = "Test",
            quantity = Decimal("1.0")
        )
        repair_me.save()
        start = datetime.date.today()
        #import pdb; pdb.set_trace()
        order = heir.generate_staged_work_order_from_resource(repair_me, "Test repair", start, self.user)
        self.assertEqual(len(order.all_processes()), 3)
        #import pdb; pdb.set_trace()
        processes = order.all_processes()
        for process in processes:
            rt = process.output_resource_types()[0]
            self.assertEqual(rt, heir)
        cts = order.all_dependent_commitments()
        work = cts.filter(event_type__relationship="work")[0]
        self.assertEqual(work.resource_type, self.work)
        #import pdb; pdb.set_trace()
