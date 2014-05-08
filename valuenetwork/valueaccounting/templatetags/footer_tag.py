from django import template

from valuenetwork.valueaccounting.models import HomePageLayout

register = template.Library()

def footer():
    try:
        layout = HomePageLayout.objects.get(id=1)
        footer = layout.footer
    except HomePageLayout.DoesNotExist:
        footer = ""
    return footer

register.simple_tag(footer)