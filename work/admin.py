from django.contrib import admin
from work.models import *
from valuenetwork.valueaccounting.actions import export_as_csv

admin.site.add_action(export_as_csv, 'export_selected objects')

class MembershipRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'agent', )
    
admin.site.register(MembershipRequest, MembershipRequestAdmin)
