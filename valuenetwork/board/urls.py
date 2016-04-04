from django.conf.urls import patterns, url
from django.views.generic.simple import direct_to_template

urlpatterns = patterns("",
    url(r'^dhen-board/(?P<context_agent_id>\d+)/$', 'valuenetwork.board.views.dhen_board', name="dhen_board"),
    url(r'^dhen-board/$', 'valuenetwork.board.views.dhen_board', name="dhen_board"),
    url(r'^add-available/(?P<context_agent_id>\d+)/$', 'valuenetwork.board.views.add_available', 
        name="add_available"),
    url(r'^receive-directly/(?P<context_agent_id>\d+)/$', 'valuenetwork.board.views.receive_directly', 
        name="receive_directly"),
    url(r'^transfer-resource/(?P<context_agent_id>\d+)/(?P<resource_id>\d+)/$', 
        'valuenetwork.board.views.transfer_resource', name="transfer_resource"),
    url(r'^purchase-resource/(?P<context_agent_id>\d+)/(?P<commitment_id>\d+)/$', 
        'valuenetwork.board.views.purchase_resource', name="purchase_resource"),
    url(r'^combine-resources/(?P<context_agent_id>\d+)/(?P<resource_type_id>\d+)/$', 
        'valuenetwork.board.views.combine_resources', name="combine_resources"),
    url(r'^change-available/(?P<commitment_id>\d+)/$', 'valuenetwork.board.views.change_available', name="change_available"),
    url(r'^undo-col2/(?P<resource_id>\d+)/$', 'valuenetwork.board.views.undo_col2', name="undo_col2"),
    url(r'^undo-col3/(?P<resource_id>\d+)/$', 'valuenetwork.board.views.undo_col3', name="undo_col3"),
    url(r'^delete-farm-commitment/(?P<commitment_id>\d+)/$', 'valuenetwork.board.views.delete_farm_commitment', name="delete_farm_commitment"),
    #url(r'^delete-receipt/(?P<resource_id>\d+)/$', 'valuenetwork.board.views.delete_receipt', name="delete_receipt"),
    
)