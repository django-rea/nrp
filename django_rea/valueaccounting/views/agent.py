import datetime
from decimal import *

from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.http import Http404, HttpResponseRedirect
from django.core.urlresolvers import reverse

from django_rea.valueaccounting.forms import AgentCreateForm, InternalExchangeNavForm
from django_rea.valueaccounting.models import *
from django_rea.valueaccounting.utils import annotate_tree_properties, project_graph
from django_rea.valueaccounting.views.generic import BaseReaAuthenticatedView, BaseReaView


class ProjectsView(BaseReaAuthenticatedView):
    template_name = "valueaccounting/projects.html"

    def get(self, request):
        EconomicAgentCls = self.get_model_class(EconomicAgent)
        projects = EconomicAgentCls.objects.context_agents()
        roots = [p for p in projects if p.is_root()]
        for root in roots:
            root.nodes = root.child_tree()
            annotate_tree_properties(root.nodes)
            # import pdb; pdb.set_trace()
            for node in root.nodes:
                aats = []
                for aat in node.agent_association_types():
                    if aat.association_behavior != "child":
                        aat.assoc_count = node.associate_count_of_type(aat.identifier)
                        assoc_list = node.all_has_associates_by_type(aat.identifier)
                        for assoc in assoc_list:
                            associations = AgentAssociation.objects.filter(is_associate=assoc, has_associate=node,
                                                                           association_type=aat)
                            if associations:
                                association = associations[0]
                                assoc.state = association.get_state_display()
                        aat.assoc_list = assoc_list
                        aats.append(aat)
                node.aats = aats
        agent_form = AgentCreateForm()
        nicks = '~'.join([
                             agt.nick for agt in EconomicAgent.objects.all()])

        return self.render_to_response({
            "roots": roots,
            "agent": agent,
            "help": self.get_help("projects"),
            "agent_form": agent_form,
            "nicks": nicks,
        })


class ProjectNetworkView(BaseReaAuthenticatedView):
    template_name = "valueaccounting/network.html"

    def get(self, request):
        producers = [p for p in ProcessType.objects.all() if p.produced_resource_types()]
        nodes, edges = project_graph(producers)
        return self.render_to_response({
            "photo_size": (128, 128),
            "nodes": nodes,
            "edges": edges,
        })


class AgentView(BaseReaAuthenticatedView):
    template_name = "valueaccounting/agent.html"

    def _get_agent(self, id):
        EconomicAgentCls = self.get_model_class(EconomicAgent)
        try:
            agent = EconomicAgentCls.objects.get(id=id)
        except EconomicAgentCls.DoesNotExist:
            raise Http404("Economic agent not found")
        return agent

    def _render(self, request, agent):
        user_agent = request.agent
        user_is_agent = user_agent == agent
        change_form = AgentCreateForm(instance=agent)
        nav_form = InternalExchangeNavForm()
        init = {"username": agent.nick, }
        user_form = UserCreationForm(initial=init)

        has_associations = agent.all_has_associates()
        is_associated_with = agent.all_is_associates()

        headings = []
        member_hours_recent = []
        member_hours_stats = []
        individual_stats = []
        member_hours_roles = []
        roles_height = 400

        membership_request = agent.membership_request()

        if agent.is_individual():
            contributions = agent.given_events.filter(is_contribution=True)
            agents_stats = {}
            for ce in contributions:
                agents_stats.setdefault(ce.resource_type, Decimal("0"))
                agents_stats[ce.resource_type] += ce.quantity
            for key, value in agents_stats.items():
                individual_stats.append((key, value))
            individual_stats.sort(lambda x, y: cmp(y[1], x[1]))

        elif agent.is_context_agent():

            subs = agent.with_all_sub_agents()
            end = datetime.date.today()
            # end = end - datetime.timedelta(days=77)
            start = end - datetime.timedelta(days=60)
            events = EconomicEvent.objects.filter(
                event_type__relationship="work",
                context_agent__in=subs,
                event_date__range=(start, end))

            if events:
                agents_stats = {}
                for event in events:
                    agents_stats.setdefault(event.from_agent.name, Decimal("0"))
                    agents_stats[event.from_agent.name] += event.quantity
                for key, value in agents_stats.items():
                    member_hours_recent.append((key, value))
                member_hours_recent.sort(lambda x, y: cmp(y[1], x[1]))

            # import pdb; pdb.set_trace()

            ces = CachedEventSummary.objects.filter(
                event_type__relationship="work",
                context_agent__in=subs)

            if ces.count():
                agents_stats = {}
                for ce in ces:
                    agents_stats.setdefault(ce.agent.name, Decimal("0"))
                    agents_stats[ce.agent.name] += ce.quantity
                for key, value in agents_stats.items():
                    member_hours_stats.append((key, value))
                member_hours_stats.sort(lambda x, y: cmp(y[1], x[1]))

                agents_roles = {}
                roles = [ce.quantity_label() for ce in ces]
                roles = list(set(roles))
                for ce in ces:
                    if ce.quantity:
                        name = ce.agent.name
                        row = [name, ]
                        for i in range(0, len(roles)):
                            row.append(Decimal("0.0"))
                            key = ce.agent.name
                        agents_roles.setdefault(key, row)
                        idx = roles.index(ce.quantity_label()) + 1
                        agents_roles[key][idx] += ce.quantity
                headings = ["Member", ]
                headings.extend(roles)
                for row in agents_roles.values():
                    member_hours_roles.append(row)
                member_hours_roles.sort(lambda x, y: cmp(x[0], y[0]))
                roles_height = len(member_hours_roles) * 20
        needs_faircoin_address = False
        if settings.USE_FAIRCOINS:
            if not agent.faircoin_address():
                needs_faircoin_address = True

        return self.render_to_response({
            "agent": agent,
            "membership_request": membership_request,
            "photo_size": (128, 128),
            "change_form": change_form,
            "user_form": user_form,
            "nav_form": nav_form,
            "user_agent": user_agent,
            "user_is_agent": user_is_agent,
            "has_associations": has_associations,
            "is_associated_with": is_associated_with,
            "headings": headings,
            "member_hours_recent": member_hours_recent,
            "member_hours_stats": member_hours_stats,
            "member_hours_roles": member_hours_roles,
            "individual_stats": individual_stats,
            "roles_height": roles_height,
            "needs_faircoin_address": needs_faircoin_address,
            "help": self.get_help("agent"),
        })

    def post(self, request, agent_id):
        agent = self._get_agent(agent_id)
        nav_form = InternalExchangeNavForm(data=request.POST or None)
        if nav_form.is_valid():
            data = nav_form.cleaned_data
            ext = data["exchange_type"]
            return HttpResponseRedirect(reverse('exchange_logging', kwargs={
                'exchange_type_id': ext.id,
                'exchange_id': 0,
                'context_agent_id': agent.id,
            }))
        else:
            return self._render(request, agent)

    def get(self, request, agent_id):
        agent = self._get_agent(agent_id)
        return self._render(request, agent)


class AgentsView(BaseReaView):
    template_name = "valueaccounting/agents.html"

    def get(self, request):
        # import pdb; pdb.set_trace()
        user_agent = request.agent
        EconomicAgentCls = self.get_model_class(EconomicAgent)
        agents = EconomicAgentCls.objects.all().order_by("agent_type__name", "name")
        agent_form = AgentCreateForm()
        nicks = '~'.join([agt.nick for agt in EconomicAgentCls.objects.all()])

        return self.render_to_response({
            "agents": agents,
            "agent_form": agent_form,
            "user_agent": user_agent,
            "help": self.get_help("agents"),
            "nicks": nicks,
        })
