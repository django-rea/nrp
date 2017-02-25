from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from django.views.generic import TemplateView
from account.views import LoginView
from django.http import HttpResponse

from django.contrib import admin
admin.autodiscover()

#from django_rea.valueaccounting.models import *


urlpatterns = patterns("",
                       url(r"^$", LoginView.as_view(template_name='account/login.html'), name='home'),
                       #url(r"^$", 'django_rea.valueaccounting.views.home', name="home"),
    url(r"^accounting/", include("django_rea.valueaccounting.urls")),
                       url(r"^admin/", include(admin.site.urls)),
                       url(r"^account/", include("account.urls")),
                       url(r"^notification/", include("pinax.notifications.urls")),
                       url(r"^equipment/", include("django_rea.equipment.urls")),
                       url(r"^board/", include("django_rea.board.urls")),
                       url(r"^work/", include("ocp.work.urls")),
                       url(r"^api/", include("django_rea.api.urls")),
                       #url(r'^report_builder/', include('report_builder.urls')),
    url(r'^comments/', include('django_comments.urls')),
                       url(r'^membership/$', 'ocp.work.views.membership_request', name="membership_request"),
                       url(r'^membershipthanks/$', TemplateView.as_view(template_name='work/membership_thanks.html'), name='membership_thanks'),
                       url(r'^captcha/', include('captcha.urls')),
                       url(r'^i18n/', include('django.conf.urls.i18n')),
                       url(r'^robots.txt$', lambda r: HttpResponse("User-agent: *\nAllow: /$\nDisallow: /", content_type="text/plain")),

                       url(r'^joinaproject/(?P<form_slug>.+)/$', 'ocp.work.views.joinaproject_request', name="joinaproject_request"),
                       url(r'^joinaproject-thanks/$', TemplateView.as_view(template_name='work/joinaproject_thanks.html'), name='joinaproject_thanks'),

                       # View URLs
    url(r'^fobi/', include('fobi.urls.view')),

                       # Edit URLs
    url(r'^fobi/', include('fobi.urls.edit')),

                       # DB Store plugin URLs
    url(r'^fobi/plugins/form-handlers/db-store/',
        include('fobi.contrib.plugins.form_handlers.db_store.urls')),
                       )

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += staticfiles_urlpatterns()
