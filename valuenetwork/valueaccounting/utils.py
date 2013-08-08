import datetime
from itertools import chain, imap
from django.contrib.contenttypes.models import ContentType
from django.utils.html import linebreaks

from valuenetwork.valueaccounting.models import Commitment, Process

def split_thousands(n, sep=','):
    s = str(n)
    if len(s) <= 3: return s  
    return split_thousands(s[:-3], sep) + sep + s[-3:]

def dfs(node, all_nodes, depth):
    """
    Performs a recursive depth-first search starting at ``node``. 
    """
    to_return = [node,]
    for subnode in all_nodes:
        if subnode.parent and subnode.parent.id == node.id:
            to_return.extend(dfs(subnode, all_nodes, depth+1))
    return to_return

def flattened_children(node, all_nodes, to_return):
     to_return.append(node)
     for subnode in all_nodes:
         if subnode.parent and subnode.parent.id == node.id:
             flattened_children(subnode, all_nodes, to_return)
     return to_return

class Edge(object):
    def __init__(self, from_node, to_node, label):
        self.from_node = from_node
        self.to_node = to_node
        self.label = label
        self.width = 1


def project_graph(producers):
    nodes = []
    edges = []
    #import pdb; pdb.set_trace()
    for p in producers:
        for rt in p.produced_resource_type_relationships():
            for pt in rt.resource_type.consuming_process_type_relationships():
                if p.project and pt.process_type.project:
                    if p.project != pt.process_type.project:
                        nodes.extend([p.project, pt.process_type.project, rt.resource_type])
                        edges.append(Edge(p.project, rt.resource_type, rt.event_type.label))
                        edges.append(Edge(rt.resource_type, pt.process_type.project, pt.inverse_label()))
    return [nodes, edges]

def explode(process_type_relationship, nodes, edges, depth, depth_limit):
    if depth > depth_limit:
        return
    #if process_type_relationship.process_type.name.startswith('Q'):
    #    return
    nodes.append(process_type_relationship.process_type)
    edges.append(Edge(
        process_type_relationship.process_type, 
        process_type_relationship.resource_type, 
        process_type_relationship.event_type.label
    ))
    for rtr in process_type_relationship.process_type.consumed_and_used_resource_type_relationships():
        nodes.append(rtr.resource_type)
        edges.append(Edge(rtr.resource_type, process_type_relationship.process_type, rtr.inverse_label()))
        for art in rtr.resource_type.producing_agent_relationships():
            nodes.append(art.agent)
            edges.append(Edge(art.agent, rtr.resource_type, art.event_type.label))
        for pt in rtr.resource_type.producing_process_type_relationships():
            explode(pt, nodes, edges, depth+1, depth_limit)

def graphify(focus, depth_limit):
    nodes = [focus]
    edges = []
    for art in focus.consuming_agent_relationships():
        nodes.append(art.agent)
        edges.append(Edge(focus, art.agent, art.event_type.label))
    for ptr in focus.producing_process_type_relationships():
        explode(ptr, nodes, edges, 0, depth_limit)
    return [nodes, edges]

def project_network():
    producers = [p for p in ProcessType.objects.all() if p.produced_resource_types()]
    nodes = []
    edges = []        
    for p in producers:
        for rt in p.produced_resource_types():
            for pt in rt.consuming_process_types():
                if p.project != pt.project:
                    nodes.extend([p.project, pt.project, rt])
                    edges.append(Edge(p.project, rt))
                    edges.append(Edge(rt, pt.project))
    return [nodes, edges]

class TimelineEvent(object):
    def __init__(self, node, start, end, title, link, description):
         self.node = node
         self.start = start
         self.end = end
         self.title = title
         self.link = link
         self.description = description

    def dictify(self):
        descrip = ""
        if self.description:
            descrip = self.description
        d = {
            "start": self.start.strftime("%b %e %Y 00:00:00 GMT-0600"),
            "title": self.title,
            "description": linebreaks(descrip),
        }
        if self.end:
            d["end"] = self.end.strftime("%b %e %Y 00:00:00 GMT-0600")
            d["durationEvent"] = True
        else:
            d["durationEvent"] = False
        if self.link:
            d["link"] = self.link
        mrq = []
        for mreq in self.node.material_requirements():
            abbrev = mreq.unit_of_quantity.abbrev or ""
            label = " ".join([
                str(mreq.quantity),
                abbrev,
                mreq.resource_type.name])
            mrq.append(label)
        d["materialReqmts"] = mrq
        trq = []
        for treq in self.node.tool_requirements():
            abbrev = treq.unit_of_quantity.abbrev or ""
            label = " ".join([
                str(treq.quantity),
                abbrev,
                treq.resource_type.name])
            trq.append(label)
        d["toolReqmts"] = trq
        wrq = []
        for wreq in self.node.work_requirements():
            abbrev = wreq.unit_of_quantity.abbrev or ""
            label = " ".join([
                str(wreq.quantity),
                abbrev,
                wreq.resource_type.name])
            wrq.append(label)
        d["workReqmts"] = wrq
        items = []
        for item in self.node.order_items():
            abbrev = item.unit_of_quantity.abbrev or ""
            label = " ".join([
                str(item.quantity),
                abbrev,
                item.resource_type.name])
            items.append(label)
        d["orderItems"] = items
        return d

def create_events(orders, processes, events):
    for order in orders:
        te = TimelineEvent(
            order,
            order.due_date,
            "",
            order.timeline_title(),
            order.get_absolute_url(),
            order.timeline_description(),
        )
        events['events'].append(te.dictify())
    for process in processes:
        te = TimelineEvent(
            process,
            process.start_date,
            process.end_date,
            process.timeline_title(),
            process.get_absolute_url(),
            process.timeline_description(),
        )
        events['events'].append(te.dictify())

def explode_events(resource_type, backsked_date, events):
    for art in resource_type.producing_agent_relationships():
        order_date = backsked_date - datetime.timedelta(days=art.lead_time)
        te = TimelineEvent(
            art,
            order_date,
            "",
            art.timeline_title(),
            resource_type.url,
            resource_type.description,
        )
        events['events'].append(te.dictify())
    for pp in resource_type.producing_process_types():
        start_date = backsked_date - datetime.timedelta(days=(pp.estimated_duration/1440))
        ppte = TimelineEvent(
            pp,
            start_date,
            backsked_date,
            pp.timeline_title(),
            pp.url,
            pp.description,
        )
        events['events'].append(ppte.dictify())
        for crt in pp.consumed_resource_types():
            explode_events(crt, start_date, events)

def backschedule_process_types(commitment, process_type,events):
    lead_time=1
    arts = None
    if commitment.from_agent:
        arts = commitment.from_agent.resource_types.filter(resource_type=commitment.resource_type)
    if arts:
        lead_time = arts[0].lead_time
    end_date = commitment.due_date - datetime.timedelta(days=lead_time)
    start_date = end_date - datetime.timedelta(days=(process_type.estimated_duration/1440))
    ppte = TimelineEvent(
        process_type,
        start_date,
        end_date,
        process_type.timeline_title(),
        process_type.url,
        process_type.description,
    )
    events['events'].append(ppte.dictify())
    for crt in process_type.consumed_resource_types():
        explode_events(crt, start_date, events)

def backschedule_process(order, process, events):
    te = TimelineEvent(
        process,
        process.start_date,
        process.end_date,
        process.timeline_title(),
        process.url,
        process.notes,
    )
    events['events'].append(te.dictify())
    for ic in process.incoming_commitments():
        te = TimelineEvent(
            ic,
            ic.due_date,
            "",
            ic.timeline_title(),
            ic.url,
            ic.description,
        )
        events['events'].append(te.dictify())
        resource_type = ic.resource_type
        pcs = resource_type.producing_commitments()
        if pcs:
            for pc in pcs:
                if pc.independent_demand == order:
                    te = TimelineEvent(
                        pc,
                        pc.due_date,
                        "",
                        pc.timeline_title(),
                        pc.url,
                        pc.description,
                    )
                    events['events'].append(te.dictify())
                    backschedule_process(order, pc.process, events)

    return events

def backschedule_order(order, events):
    te = TimelineEvent(
        order,
        order.due_date,
        "",
        order.timeline_title(),
        "",
        order.description,
    )
    events['events'].append(te.dictify())
    for pc in order.producing_commitments():
        te = TimelineEvent(
            pc,
            pc.due_date,
            "",
            pc.timeline_title(),
            pc.url,
            pc.description,
        )
        events['events'].append(te.dictify())
        backschedule_process(order, pc.process, events)

#todo: obsolete, replaced by Process.explode_demands
def recursively_explode_demands(process, order, user, visited):
    """This method assumes the output commitment from the process 

        has already been created.

    """
    #import pdb; pdb.set_trace()
    pt = process.process_type
    output = process.main_outgoing_commitment()
    if output.resource_type not in visited:
        visited.append(output.resource_type)
    for ptrt in pt.all_input_resource_type_relationships():        
        commitment = Commitment(
            independent_demand=order,
            event_type=ptrt.event_type,
            description=ptrt.description,
            due_date=process.start_date,
            resource_type=ptrt.resource_type,
            process=process,
            project=pt.project,
            quantity=output.quantity * ptrt.quantity,
            unit_of_quantity=ptrt.resource_type.unit,
            created_by=user,
        )
        commitment.save()
        if ptrt.resource_type not in visited:
            visited.append(ptrt.resource_type)
            qty_to_explode = commitment.net()
            if qty_to_explode:
                pptr = ptrt.resource_type.main_producing_process_type_relationship()
                if pptr:
                    next_pt = pptr.process_type
                    start_date = process.start_date - datetime.timedelta(minutes=next_pt.estimated_duration)
                    next_process = Process(          
                        name=next_pt.name,
                        process_type=next_pt,
                        process_pattern=next_pt.process_pattern,
                        project=next_pt.project,
                        url=next_pt.url,
                        end_date=process.start_date,
                        start_date=start_date,
                    )
                    next_process.save()
                    next_commitment = Commitment(
                        independent_demand=order,
                        event_type=pptr.event_type,
                        description=pptr.description,
                        due_date=process.start_date,
                        resource_type=pptr.resource_type,
                        process=next_process,
                        project=next_pt.project,
                        quantity=qty_to_explode * pptr.quantity,
                        unit_of_quantity=pptr.resource_type.unit,
                        created_by=user,
                    )
                    next_commitment.save()
                    recursively_explode_demands(next_process, order, user, visited)

class XbillNode(object):
    def __init__(self, node, depth):
         self.node = node
         self.depth = depth
         self.open = False
         self.close = []
         self.xbill_class = self.node.xbill_class()

    def xbill_object(self):
        return self.node.xbill_child_object()

    def xbill_label(self):
        return self.node.xbill_label()

    def xbill_explanation(self):
        return self.node.xbill_explanation()

    #def category(self):
    #    return self.node.xbill_category()


def xbill_dfs(node, all_nodes, visited, depth):
    """
    Performs a recursive depth-first search starting at ``node``. 
    """
    to_return = []
    if node not in visited:
        visited.append(node)
        #to_return = [XbillNode(node,depth),]
        to_return.append(XbillNode(node,depth))
        #print "+created node:+", node, depth
        for subnode in all_nodes:
            parents = subnode.xbill_parent_object().xbill_parents()
            xclass = subnode.xbill_class()
            if not subnode is node:
                if parents and node in parents:
                    #print "*active node:*", node, "*depth:*", depth, "*subnode:*", subnode, "*parent_object:*", subnode.xbill_parent_object(), "*parents:*", parents
                    #import pdb; pdb.set_trace()
                    to_return.extend(xbill_dfs(subnode, all_nodes, visited, depth+1))
    return to_return

def explode_xbill_children(node, nodes, exploded):
    if node not in nodes:
        nodes.append(node)
        #import pdb; pdb.set_trace()
        xclass = node.xbill_class()
        explode = True
        if xclass == 'process-type':
            #import pdb; pdb.set_trace()
            pt = node.process_type
            if pt in exploded:
                explode = False
            else:
                exploded.append(pt)
        if explode:
            for kid in node.xbill_child_object().xbill_children():
                explode_xbill_children(kid, nodes, exploded)

def generate_xbill(resource_type):
    nodes = []
    exploded = []
    for kid in resource_type.xbill_children():
        explode_xbill_children(kid, nodes, exploded)
    nodes = list(set(nodes))
    #import pdb; pdb.set_trace()
    to_return = []
    visited = []
    for kid in resource_type.xbill_children():
        to_return.extend(xbill_dfs(kid, nodes, visited, 1))
    annotate_tree_properties(to_return)
    #to_return.sort(lambda x, y: cmp(x.xbill_object().name,
    #                                y.xbill_object().name))
    return to_return


#adapted from threaded_comments.util
def annotate_tree_properties(nodes):
    """
    iterate through nodes and adds some magic properties to each of them
    representing opening list of children and closing it
    """
    if not nodes:
        return

    it = iter(nodes)

    # get the first item, this will fail if no items !
    old = it.next()

    # first item starts a new thread
    old.open = True
    for c in it:

        # increase the depth
        if c.depth > old.depth:
            c.open = True

        else: # c.depth <= old.depth
            # close some depths
            old.close = range(old.depth - c.depth)

        # iterate
        old = c

    old.close = range(old.depth)

