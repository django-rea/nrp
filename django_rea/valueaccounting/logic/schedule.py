from decimal import *


# todo: soon to be obsolete (is it obsolete now?)
def explode_dependent_demands(commitment, user):
    """This method assumes an input commitment"""

    # import pdb; pdb.set_trace()
    qty_to_explode = commitment.net()
    if qty_to_explode:
        rt = commitment.resource_type
        # todo: add stage and state as args?
        # todo pr: this shd probably use own_or_parent_recipes
        ptrt, inheritance = rt.main_producing_process_type_relationship()
        demand = commitment.independent_demand
        if ptrt:
            pt = ptrt.process_type
            start_date = commitment.due_date - datetime.timedelta(minutes=pt.estimated_duration)
            feeder_process = Process(
                name=pt.name,
                process_type=pt,
                process_pattern=pt.process_pattern,
                context_agent=pt.context_agent,
                url=pt.url,
                end_date=commitment.due_date,
                start_date=start_date,
                created_by=user,
            )
            feeder_process.save()
            # todo: sub process.add_commitment()
            output_commitment = Commitment(
                independent_demand=demand,
                order_item=commitment.order_item,
                event_type=ptrt.event_type,
                due_date=commitment.due_date,
                resource_type=rt,
                process=feeder_process,
                context_agent=pt.context_agent,
                quantity=qty_to_explode,
                unit_of_quantity=rt.unit,
                description=ptrt.description,
                created_by=user,
            )
            output_commitment.save()
            recursively_explode_demands(feeder_process, demand, user, [])


def handle_commitment_changes(old_ct, new_rt, new_qty, old_demand, new_demand):
    propagators = []
    explode = True
    if old_ct.event_type.relationship == "out":
        dependants = old_ct.process.incoming_commitments()
        propagators.append(old_ct)
        if new_qty != old_ct.quantity:
            explode = False
    else:
        dependants = old_ct.associated_producing_commitments()
    old_rt = old_ct.resource_type
    order_item = old_ct.order_item

    if not propagators:
        for dep in dependants:
            if order_item:
                if dep.order_item == order_item:
                    propagators.append(dep)
                    explode = False
            else:
                if dep.due_date == old_ct.process.start_date:
                    if dep.quantity == old_ct.quantity:
                        propagators.append(dep)
                        explode = False
    if new_rt != old_rt:
        for ex_ct in old_ct.associated_producing_commitments():
            if ex_ct.order_item == order_item:
                ex_ct.delete_dependants()
        old_ct.delete()
        explode = True
    elif new_qty != old_ct.quantity:
        delta = new_qty - old_ct.quantity
        for pc in propagators:
            if new_demand != old_demand:
                propagate_changes(pc, delta, old_demand, new_demand, [])
            else:
                propagate_qty_change(pc, delta, [])
    else:
        if new_demand != old_demand:
            # this is because we are just changing the order
            delta = Decimal("0")
            for pc in propagators:
                propagate_changes(pc, delta, old_demand, new_demand, [])
            explode = False

    return explode


def propagate_qty_change(commitment, delta, visited):
    # import pdb; pdb.set_trace()
    process = commitment.process
    if commitment not in visited:
        visited.append(commitment)
        for ic in process.incoming_commitments():
            if ic.event_type.relationship != "cite":
                input_ctype = ic.commitment_type()
                output_ctype = commitment.commitment_type()
                ratio = input_ctype.quantity / output_ctype.quantity
                new_delta = (delta * ratio).quantize(Decimal('.01'), rounding=ROUND_UP)

                ic.quantity += new_delta
                ic.save()
                # import pdb; pdb.set_trace()
                rt = ic.resource_type
                pcs = ic.associated_producing_commitments()
                if pcs:
                    oh_qty = 0
                    if rt.substitutable:
                        if ic.event_type.resource_effect == "-":
                            oh_qty = rt.onhand_qty_for_commitment(ic)
                    if oh_qty:
                        delta_delta = ic.quantity - oh_qty
                        new_delta = delta_delta
                order_item = ic.order_item
                for pc in pcs:
                    if pc.order_item == order_item:
                        propagate_qty_change(pc, new_delta, visited)
    commitment.quantity += delta
    commitment.save()


def propagate_changes(commitment, delta, old_demand, new_demand, visited):
    # import pdb; pdb.set_trace()
    process = commitment.process
    order_item = commitment.order_item
    if process not in visited:
        visited.append(process)
        for ic in process.incoming_commitments():
            ratio = ic.quantity / commitment.quantity
            new_delta = (delta * ratio).quantize(Decimal('.01'), rounding=ROUND_UP)
            ic.quantity += new_delta
            ic.order_item = order_item
            ic.save()
            rt = ic.resource_type
            for pc in ic.associated_producing_commitments():
                if pc.order_item == order_item:
                    propagate_changes(pc, new_delta, old_demand, new_demand, visited)
    commitment.quantity += delta
    commitment.independent_demand = new_demand
    commitment.save()
