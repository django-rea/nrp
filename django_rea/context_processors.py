from django.contrib.sites.models import Site


def settings(request):
    ctx = {}
    if Site._meta.installed:
        site = Site.objects.get_current()
        ctx.update({
            "site_name": site.name,
            "site_domain": site.domain
        })
    return ctx