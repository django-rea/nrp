from django.conf.urls import url
from django.views.generic import TemplateView
import django_rea.board.views

urlpatterns = [
                       url(r'^dhen-board/(?P<context_agent_id>\d+)/$', django_rea.board.views.dhen_board, name="dhen_board"),
                       url(r'^dhen-board/$', django_rea.board.views.dhen_board, name="dhen_board"),
                       url(r'^add-available/(?P<context_agent_id>\d+)/$', django_rea.board.views.add_available,
                           name="add_available"),
                       url(r'^receive-directly/(?P<context_agent_id>\d+)/$', django_rea.board.views.receive_directly,
                           name="receive_directly"),
                       url(r'^transfer-resource/(?P<context_agent_id>\d+)/(?P<resource_id>\d+)/$',
                           django_rea.board.views.transfer_resource, name="transfer_resource"),
                       url(r'^purchase-resource/(?P<context_agent_id>\d+)/(?P<commitment_id>\d+)/$',
                           django_rea.board.views.purchase_resource, name="purchase_resource"),
                       url(r'^combine-resources/(?P<context_agent_id>\d+)/(?P<resource_type_id>\d+)/$',
                           django_rea.board.views.combine_resources, name="combine_resources"),
                       url(r'^change-available/(?P<commitment_id>\d+)/$', django_rea.board.views.change_available, name="change_available"),
                       url(r'^undo-col2/(?P<resource_id>\d+)/$', django_rea.board.views.undo_col2, name="undo_col2"),
                       url(r'^undo-col3/(?P<resource_id>\d+)/$', django_rea.board.views.undo_col3, name="undo_col3"),
                       url(r'^delete-farm-commitment/(?P<commitment_id>\d+)/$',
                           django_rea.board.views.delete_farm_commitment, name="delete_farm_commitment"),
                       #url(r'^delete-receipt/(?P<resource_id>\d+)/$', django_rea.board.views.delete_receipt, name="delete_receipt"),

                       ]
