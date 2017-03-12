from django.contrib.sites.models import Site


def camelcase(name):
    return ''.join(x.capitalize() or ' ' for x in name.split(' '))


def camelcase_lower(name):
    pname = camelcase(name)
    return pname[0].lower() + pname[1:]


def split_thousands(n, sep=','):
    s = str(n)
    if len(s) <= 3: return s
    return split_thousands(s[:-3], sep) + sep + s[-3:]


def get_url_starter():
    return "".join(["https://", Site.objects.get_current().domain])
