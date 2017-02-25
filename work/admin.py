from django.contrib import admin
from work.models import *
from django_rea.valueaccounting.actions import export_as_csv

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

class NewFeatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'deployment_date', 'description', 'url',)

admin.site.register(NewFeature, NewFeatureAdmin)

#this won't work unless I can set the created_by field from django admin
#class InvoiceNumberAdmin(admin.ModelAdmin):
#    list_display = ('invoice_number', 'member', 'description', 'created_by',)

#admin.site.register(InvoiceNumber, InvoiceNumberAdmin)
