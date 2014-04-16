import datetime
from itertools import chain, imap

from django.contrib.contenttypes.models import ContentType
from django.utils.html import linebreaks
from django.contrib.sites.models import Site

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
     
def flattened_children_by_association(node, all_associations, to_return): #works only for agents
    #import pdb; pdb.set_trace()
    to_return.append(node)
    for association in all_associations:
        if association.to_agent.id == node.id and association.association_type.identifier == "child":
            flattened_children_by_association(association.from_agent, all_associations, to_return)
    return to_return
    
def agent_dfs_by_association(node, all_associations, depth): #works only for agents
    #import pdb; pdb.set_trace()
    node.depth = depth
    to_return = [node,]
    for association in all_associations:
        if association.to_agent.id == node.id and association.association_type.identifier == "child":
            to_return.extend(agent_dfs_by_association(association.from_agent, all_associations, depth+1))
    return to_return

class Edge(object):
    def __init__(self, from_node, to_node, label):
        self.from_node = from_node
        self.to_node = to_node
        self.label = label
        self.width = 1

    def dictify(self):
        d = {
            "from_node": self.from_node.node_id(),
            "to_node": self.to_node.node_id(),
            "label": self.label,
            "width": self.width,
        }
        return d

def process_link_label(from_process, to_process):
    outputs = [oc.resource_type for oc in from_process.outgoing_commitments()]
    inputs = [ic.resource_type for ic in to_process.incoming_commitments()]
    intersect = set(outputs) & set(inputs)
    label = ", ".join(rt.name for rt in intersect)
    return label
            
def process_graph(processes):
    nodes = []
    visited = set()
    connections = set()
    edges = []
    for p in processes:
        if p not in visited:
            visited.add(p)
            project_id = ""
            if p.project:
                project_id = p.project.node_id()
            d = {
                "id": p.node_id(),
                "name": p.name,
                "project-id": project_id,
                "start": p.start_date.strftime('%Y-%m-%d'),
                "end": p.end_date.strftime('%Y-%m-%d'),
                }
            nodes.append(d)
        next = p.next_processes()
        for n in next:
            if n not in visited:
                visited.add(n)
                project_id = ""
                if p.project:
                    project_id = p.project.node_id()
                d = {
                    "id": n.node_id(),
                    "name": n.name,
                    "project-id": project_id,
                    "start": n.start_date.strftime('%Y-%m-%d'),
                    "end": n.end_date.strftime('%Y-%m-%d'),
                    }
                nodes.append(d)
            c = "-".join([str(p.id), str(n.id)])
            if c not in connections:
                connections.add(c)
                label = process_link_label(p, n)
                edge = Edge(p, n, label)
                edges.append(edge.dictify())
        prev = p.previous_processes()
        for n in prev:
            if n not in visited:
                visited.add(n)
                project_id = ""
                if p.project:
                    project_id = p.project.node_id()
                d = {
                    "id": n.node_id(),
                    "name": n.name,
                    "project-id": project_id,
                    "start": n.start_date.strftime('%Y-%m-%d'),
                    "end": n.end_date.strftime('%Y-%m-%d'),
                    }
                nodes.append(d)
            c = "-".join([str(n.id), str(p.id)])
            if c not in connections:
                connections.add(c)
                label = process_link_label(n, p)
                edge = Edge(n, p, label)
                edges.append(edge.dictify())
    big_d = {
        "nodes": nodes,
        "edges": edges,
    }
    return big_d

def project_process_resource_agent_graph(project_list, process_list):
    projects = {}
    processes = {}
    resource_types = {}
    rt_set = set()
    orders = {}
    order_set = set()
    agents = {}
    agent_dict = {}
    current_site = Site.objects.get_current()
    url_starter = "".join(["http://", current_site.domain])
    #url_starter = "http://valnet.webfactional.com"
    #url_starter = ""
    for p in project_list:
        d = {
            "name": p.name,
            }
        projects[p.node_id()] = d   
    for p in process_list:
        project_id = ""
        if p.project:
            project_id = p.project.node_id()
        order_id = ""
        order = p.independent_demand()
        if order:
            order_id = order.node_id()
            if order not in order_set:
                order_set.add(order)
        dp = {
            "name": p.name,
            "type": "process",
            "url": "".join([url_starter, p.get_absolute_url()]),
            "project-id": project_id,
            "order-id": order_id,
            "start": p.start_date.strftime('%Y-%m-%d'),
            "end": p.end_date.strftime('%Y-%m-%d'),
            "orphan": p.is_orphan(),
            "next": []
            }
        processes[p.node_id()] = dp
        p.dp = dp
        rts = p.output_resource_types()
        for rt in rts:
            if rt not in rt_set:
                rt_set.add(rt)
        next_ids = [rt.node_id() for rt in p.output_resource_types()]
        dp["next"].extend(next_ids)       
        agnts = p.working_agents()
        for a in agnts:
            if a not in agent_dict:
                agent_dict[a] = []
            agent_dict[a].append(p)
    for rt in rt_set:
        drt = {
            "name": rt.name,
            "type": "resourcetype",
            "url": "".join([url_starter, rt.get_absolute_url()]),
            "photo-url": rt.photo_url,
            "next": []
            }
        for p in rt.wanting_processes():
            p_id = p.node_id()
            if p_id in processes:
                drt["next"].append(p_id)
        resource_types[rt.node_id()] = drt
    for order in order_set:
        receiver_name = ""
        if order.receiver:
            receiver_name = order.receiver.name
        dord = {
            "name": order.__unicode__(),
            "type": "order",
            "for": receiver_name,
            "due": order.due_date.strftime('%Y-%m-%d'),
            "url": "".join([url_starter, order.get_absolute_url()]),
            "processes": []
            }
        for p in order.all_processes():
            p_id = p.node_id()
            if p_id in processes:
                dord["processes"].append(p_id)
        orders[order.node_id()] = dord
    for agnt, procs in agent_dict.items():
        da = {
            "name": agnt.name,
            "type": "agent",
            "processes": []
            }
        for p in procs:
            da["processes"].append(p.node_id())
        agents[agnt.node_id()] = da
    big_d = {
        "projects": projects,
        "processes": processes,
        "agents": agents,
        "resource_types": resource_types,
        "orders": orders,
    }
    return big_d

def project_process_graph(project_list, process_list):
    projects = {}
    processes = {}
    agents = {}
    agent_dict = {}
    for p in project_list:
        d = {
            "name": p.name,
            }
        projects[p.node_id()] = d   
    for p in process_list:
        project_id = ""
        if p.project:
            project_id = p.project.node_id()
        dp = {
            "name": p.name,
            "project-id": project_id,
            "start": p.start_date.strftime('%Y-%m-%d'),
            "end": p.end_date.strftime('%Y-%m-%d'),
            "next": []
            }
        processes[p.node_id()] = dp
        p.dp = dp
        agnts = p.working_agents()
        for a in agnts:
            if a not in agent_dict:
                agent_dict[a] = []
            agent_dict[a].append(p)
    for p in process_list:
        next_ids = [n.node_id() for n in p.next_processes()]
        p.dp["next"].extend(next_ids)
    for agnt, procs in agent_dict.items():
        da = {
            "name": agnt.name,
            "processes": []
            }
        for p in procs:
            da["processes"].append(p.node_id())
        agents[agnt.node_id()] = da
    big_d = {
        "projects": projects,
        "processes": processes,
        "agents": agents,
    }
    return big_d      
            
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
        for mreq in self.node.consumed_input_requirements():
            abbrev = mreq.unit_of_quantity.abbrev or ""
            label = " ".join([
                str(mreq.quantity),
                abbrev,
                mreq.resource_type.name])
            mrq.append(label)
        d["consumableReqmts"] = mrq
        trq = []
        for treq in self.node.used_input_requirements():
            abbrev = treq.unit_of_quantity.abbrev or ""
            label = " ".join([
                str(treq.quantity),
                abbrev,
                treq.resource_type.name])
            trq.append(label)
        d["usableReqmts"] = trq
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
        prevs = []
        try:
            for p in self.node.previous_processes():
                label = "~".join([
                    p.get_absolute_url(),
                    p.name])
                prevs.append(label)
        except:
            pass
        d["previous"] = prevs
        next = []
        try:
            for p in self.node.next_processes():
                label = "~".join([
                    p.get_absolute_url(),
                    p.name])
                next.append(label)
        except:
            pass
        d["next"] = next
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
            if subnode.node_id() != node.node_id():
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

#todo: obsolete
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

