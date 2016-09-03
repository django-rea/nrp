from django.contrib import admin
from work.models import *
from valuenetwork.valueaccounting.actions import export_as_csv

admin.site.add_action(export_as_csv, 'export_selected objects')

class MembershipRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'agent', )

admin.site.register(MembershipRequest, MembershipRequestAdmin)

class SkillSuggestionAdmin(admin.ModelAdmin):
    list_display = ('skill', 'suggested_by', 'suggestion_date', )

admin.site.register(SkillSuggestion, SkillSuggestionAdmin)

class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'agent', )

admin.site.register(JoinRequest, JoinRequestAdmin)
