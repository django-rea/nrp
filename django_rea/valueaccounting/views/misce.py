from decimal import *
from collections import OrderedDict

from django.conf import settings

from django_rea.annotations import split_apart
from django_rea.valueaccounting.forms import TodoForm
from django_rea.valueaccounting.models import PatternUseCase
from django_rea.valueaccounting.models.misc import HomePageLayout
from django_rea.valueaccounting.models.schedule import Commitment
from django_rea.valueaccounting.views.generic import BaseReaView


class HomeView(BaseReaView):
    template_name = 'homepage.html'

    def get(self, request):
        layout = None
        try:
            layout = HomePageLayout.objects.get(id=1)
        except HomePageLayout.DoesNotExist:
            pass
        template_params = {
            "layout": layout,
            "photo_size": (128, 128),
            "help": self.get_help("home"),
        }
        if layout:
            if layout.use_work_panel:
                template_params["work_to_do"] = Commitment.objects.unfinished().filter(
                    from_agent=None,
                    event_type__relationship="work"
                )
            if layout.use_needs_panel:
                # todo: reqs needs a lot of work
                reqs = Commitment.objects.to_buy()
                stuff = OrderedDict()
                for req in reqs:
                    if req.resource_type not in stuff:
                        stuff[req.resource_type] = Decimal("0")
                    stuff[req.resource_type] += req.purchase_quantity
                template_params["stuff_to_buy"] = stuff
            if layout.use_creations_panel:
                vcs = Commitment.objects.filter(event_type__relationship="out")
                value_creations = []
                rts = []
                for vc in vcs:
                    if vc.fulfilling_events():
                        if vc.resource_type not in rts:
                            rts.append(vc.resource_type)
                            value_creations.append(vc)
                template_params["value_creations"] = value_creations
        return self.render_to_response(template_params)


class StartView(BaseReaView):
    template_name = "valueaccounting/start.html"

    @split_apart(layer="PROJECTS")
    def get(self, request):
        my_work = []
        my_skillz = []
        other_wip = []
        if request.agent:
            my_work = Commitment.objects.unfinished().filter(
                event_type__relationship="work",
                from_agent=request.agent)
            skill_ids = request.agent.resource_types.values_list('resource_type__id', flat=True)
            my_skillz = Commitment.objects.unfinished().filter(
                from_agent=None,
                event_type__relationship="work",
                resource_type__id__in=skill_ids)
            other_unassigned = Commitment.objects.unfinished().filter(
                from_agent=None,
                event_type__relationship="work").exclude(resource_type__id__in=skill_ids)
        else:
            other_unassigned = Commitment.objects.unfinished().filter(
                from_agent=None,
                event_type__relationship="work")
        todos = Commitment.objects.todos().filter(from_agent=request.agent)
        init = {"from_agent": request.agent, }
        patterns = PatternUseCase.objects.filter(use_case__identifier='todo')
        if patterns:
            pattern = patterns[0].pattern
            todo_form = TodoForm(pattern=pattern, initial=init)
        else:
            todo_form = TodoForm(initial=init)
        work_now = settings.USE_WORK_NOW
        return self.render_to_response({
            "agent": request.agent,
            "my_work": my_work,
            "my_skillz": my_skillz,
            "other_unassigned": other_unassigned,
            "todos": todos,
            "todo_form": todo_form,
            "work_now": work_now,
            "help": self.get_help("my_work"),
        })
