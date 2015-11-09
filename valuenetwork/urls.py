from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from django.views.generic.simple import direct_to_template

from django.contrib import admin
admin.autodiscover()

#from valuenetwork.valueaccounting.models import *


urlpatterns = patterns("",
    url(r"^$", 'valuenetwork.valueaccounting.views.home', name="home"),
    url(r"^accounting/", include("valuenetwork.valueaccounting.urls")),
    url(r"^admin/", include(admin.site.urls)),
    url(r"^account/", include("account.urls")),
    url(r"^notification/", include("notification.urls")),    
    url(r"^equipment/", include("valuenetwork.equipment.urls")),
    url(r"^board/", include("valuenetwork.board.urls")),
    url(r"^api/", include("valuenetwork.api.urls")),
    #url(r'^report_builder/', include('report_builder.urls')),
)

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += staticfiles_urlpatterns()
