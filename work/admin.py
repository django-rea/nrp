from django.contrib import admin
from work.models import *
from valuenetwork.valueaccounting.actions import export_as_csv

admin.site.add_action(export_as_csv, 'export_selected objects')

class MembershipRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'state', 'agent', )

admin.site.register(MembershipRequest, MembershipRequestAdmin)

class SkillSuggestionAdmin(admin.ModelAdmin):
    list_display = ('skill', 'suggested_by', 'suggestion_date', 'state', 'resource_type', )

admin.site.register(SkillSuggestion, SkillSuggestionAdmin)

class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'state', 'project', 'agent',)
    #fields = ('name', 'state', 'project', 'agent',)
    #list_editable = ['state',]

admin.site.register(JoinRequest, JoinRequestAdmin)

class ProjectAdmin(admin.ModelAdmin):
    list_display = ('agent', 'visibility', 'joining_style', 'fobi_slug',)

admin.site.register(Project, ProjectAdmin)
