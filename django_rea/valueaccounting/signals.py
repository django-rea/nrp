from django.utils.translation import ugettext_noop as _
from django.db.models.signals import post_migrate
from django.conf import settings

from .models import *


if "pinax.notifications" in settings.INSTALLED_APPS:
    from pinax.notifications import models as notification

    def create_notice_types(verbosity, **kwargs):
        notification.NoticeType.create("valnet_join_task", _("Join Task"), _("a colleaque wants to help with this task"), default=2)
        notification.NoticeType.create("valnet_help_wanted", _("Help Wanted"), _("a colleague requests help that fits your skills"), default=2)
        notification.NoticeType.create("valnet_new_task", _("New Task"), _("a new task was posted that fits your skills"), default=2)
        notification.NoticeType.create("valnet_new_todo", _("New Todo"), _("a new todo was posted that is assigned to you"), default=2)
        notification.NoticeType.create("valnet_deleted_todo", _("Deleted Todo"), _("a todo that was assigned to you has been deleted"), default=2)
        notification.NoticeType.create("valnet_distribution", _("New Distribution"), _("you have received a new income distribution"), default=2)
        notification.NoticeType.create("valnet_payout_request", _("Payout Request"), _("you have received a new payout request"), default=2)
        notification.NoticeType.create("work_membership_request", _("Freedom Coop Membership Request"), _("we have received a new membership request"), default=2)
        notification.NoticeType.create("work_join_request", _("Project Join Request"), _("we have received a new join request"), default=2)
        notification.NoticeType.create("work_new_account", _("Project New OCP Account"), _("a new OCP account details"), default=2)
        notification.NoticeType.create("comment_membership_request", _("Comment in Freedom Coop Membership Request"), _("we have received a new comment in a membership request"), default=2)
        notification.NoticeType.create("comment_join_request", _("Comment in Project Join Request"), _("we have received a new comment in a join request"), default=2)
        notification.NoticeType.create("work_skill_suggestion", _("Skill suggestion"), _("we have received a new skill suggestion"), default=2)
        print "created valueaccounting notice types"
    post_migrate.connect(create_notice_types)
else:
    print "Skipping creation of valueaccounting NoticeTypes as notification app not found"

#def create_agent_types(app, **kwargs):
#    if app != "valueaccounting":
#        return
def create_agent_types(**kwargs):
    AgentType.create('Individual', 'individual', False)
    AgentType.create('Organization', 'org', False)
    AgentType.create('Network', 'network', True)
    print "created agent types"

post_migrate.connect(create_agent_types)


#def create_agent_association_types(app, **kwargs):
#    if app != "valueaccounting":
#        return
def create_agent_association_types(**kwargs):
    AgentAssociationType.create('child', 'Child', 'Children', 'child', 'is child of', 'has child')
    AgentAssociationType.create('member', 'Member', 'Members', 'member', 'is member of', 'has member')
    AgentAssociationType.create('supplier', 'Supplier', 'Suppliers', 'supplier', 'is supplier of', 'has supplier')
    AgentAssociationType.create('customer', 'Customer', 'Customers', 'customer', 'is customer of', 'has customer')
    print "created agent association types"

post_migrate.connect(create_agent_association_types)


#def create_use_cases(app, **kwargs):
#    if app != "valueaccounting":
#        return
def create_use_cases(**kwargs):
    #UseCase.create('cash_contr', _('Cash Contribution'), True)
    UseCase.create('non_prod', _('Non-production Logging'), True)
    UseCase.create('rand', _('Manufacturing Recipes/Logging'))
    UseCase.create('recipe', _('Workflow Recipes/Logging'))
    UseCase.create('todo', _('Todos'), True)
    UseCase.create('cust_orders', _('Customer Orders'))
    UseCase.create('purchasing', _('Purchasing'))
    #UseCase.create('res_contr', _('Material Contribution'))
    #UseCase.create('purch_contr', _('Purchase Contribution'))
    #UseCase.create('exp_contr', _('Expense Contribution'), True)
    #UseCase.create('sale', _('Sale'))
    UseCase.create('distribution', _('Distribution'), True)
    UseCase.create('val_equation', _('Value Equation'), True)
    UseCase.create('payout', _('Payout'), True)
    #UseCase.create('transfer', _('Transfer'))
    UseCase.create('available', _('Make Available'), True)
    UseCase.create('intrnl_xfer', _('Internal Exchange'))
    UseCase.create('supply_xfer', _('Incoming Exchange'))
    UseCase.create('demand_xfer', _('Outgoing Exchange'))
    print "created use cases"

post_migrate.connect(create_use_cases)


#def create_event_types(app, **kwargs):
#    if app != "valueaccounting":
#        return
def create_event_types(**kwargs):
    #Keep the first column (name) as unique
    EventType.create('Citation', _('cites'), _('cited by'), 'cite', 'process', '=', '')
    EventType.create('Resource Consumption', _('consumes'), _('consumed by'), 'consume', 'process', '-', 'quantity')
    #EventType.create('Cash Contribution', _('contributes cash'), _('cash contributed by'), 'cash', 'exchange', '+', 'value')
    #EventType.create('Donation', _('donates cash'), _('cash donated by'), 'cash', 'exchange', '+', 'value')
    #EventType.create('Resource Contribution', _('contributes resource'), _('resource contributed by'), 'resource', 'exchange', '+', 'quantity')
    EventType.create('Damage', _('damages'), _('damaged by'), 'out', 'agent', '-', 'value')
    #EventType.create('Expense', _('expense'), '', 'expense', 'exchange', '=', 'value')
    EventType.create('Failed quantity', _('fails'), '', 'out', 'process', '<', 'quantity')
    #EventType.create('Payment', _('pays'), _('paid by'), 'pay', 'exchange', '-', 'value')
    EventType.create('Resource Production', _('produces'), _('produced by'), 'out', 'process', '+', 'quantity')
    EventType.create('Work Provision', _('provides'), _('provided by'), 'out', 'agent', '+', 'time')
    #EventType.create('Receipt', _('receives'), _('received by'), 'receive', 'exchange', '+', 'quantity')
    EventType.create('Sale', _('sells'), _('sold by'), 'out', 'agent', '=', '')
    #EventType.create('Shipment', _('ships'), _('shipped by'), 'shipment', 'exchange', '-', 'quantity')
    EventType.create('Supply', _('supplies'), _('supplied by'), 'out', 'agent', '=', '')
    EventType.create('Todo', _('todo'), '', 'todo', 'agent', '=', '')
    EventType.create('Resource use', _('uses'), _('used by'), 'use', 'process', '=', 'time')
    EventType.create('Time Contribution', _('work'), '', 'work', 'process', '=', 'time')
    EventType.create('Create Changeable', _('creates changeable'), 'changeable created', 'out', 'process', '+~', 'quantity')
    EventType.create('To Be Changed', _('to be changed'), '', 'in', 'process', '>~', 'quantity')
    EventType.create('Change', _('changes'), 'changed', 'out', 'process', '~>', 'quantity')
    EventType.create('Adjust Quantity', _('adjusts'), 'adjusted', 'adjust', 'agent', '+-', 'quantity')
    #EventType.create('Cash Receipt', _('receives cash'), _('cash received by'), 'receivecash', 'exchange', '+', 'value')
    EventType.create('Distribution', _('distributes'), _('distributed by'), 'distribute', 'distribution', '+', 'value')
    EventType.create('Cash Disbursement', _('disburses cash'), _('disbursed by'), 'disburse', 'distribution', '-', 'value')
    EventType.create('Payout', _('pays out'), _('paid by'), 'payout', 'agent', '-', 'value')
    #EventType.create('Loan', _('loans'), _('loaned by'), 'cash', 'exchange', '+', 'value')
    #EventType.create('Transfer', _('transfers'), _('transfered by'), 'transfer', 'exchange', '=', 'quantity')
    #EventType.create('Reciprocal Transfer', _('reciprocal transfers'), _('transfered by'), 'transfer', 'exchange', '=', 'quantity')
    #EventType.create('Fee', _('fees'), _('charged by'), 'fee', 'exchange', '-', 'value')
    EventType.create('Give', _('gives'), _('given by'), 'give', 'transfer', '-', 'quantity')
    EventType.create('Receive', _('receives'), _('received by'), 'receive', 'exchange', '+', 'quantity')
    #EventType.create('Make Available', _('makes available'), _('made available by'), 'available', 'agent', '+', 'quantity')

    print "created event types"

post_migrate.connect(create_event_types)


#def create_usecase_eventtypes(app, **kwargs):
#    if app != "valueaccounting":
#        return
def create_usecase_eventtypes(**kwargs):
    #UseCaseEventType.create('cash_contr', 'Time Contribution')
    #UseCaseEventType.create('cash_contr', 'Cash Contribution')
    #UseCaseEventType.create('cash_contr', 'Donation')
    UseCaseEventType.create('non_prod', 'Time Contribution')
    UseCaseEventType.create('rand', 'Citation')
    UseCaseEventType.create('rand', 'Resource Consumption')
    UseCaseEventType.create('rand', 'Resource Production')
    UseCaseEventType.create('rand', 'Resource use')
    UseCaseEventType.create('rand', 'Time Contribution')
    UseCaseEventType.create('rand', 'To Be Changed')
    UseCaseEventType.create('rand', 'Change')
    UseCaseEventType.create('rand', 'Create Changeable')
    #UseCaseEventType.create('rand', 'Process Expense')
    #todo: 'rand' now = mfg/assembly, 'recipe' now = workflow.  Need to rename these use cases.
    UseCaseEventType.create('recipe','Citation')
    UseCaseEventType.create('recipe', 'Resource Consumption')
    UseCaseEventType.create('recipe', 'Resource Production')
    UseCaseEventType.create('recipe', 'Resource use')
    UseCaseEventType.create('recipe', 'Time Contribution')
    UseCaseEventType.create('recipe', 'To Be Changed')
    UseCaseEventType.create('recipe', 'Change')
    UseCaseEventType.create('recipe', 'Create Changeable')
    #UseCaseEventType.create('recipe', 'Process Expense')
    UseCaseEventType.create('todo', 'Todo')
    #UseCaseEventType.create('cust_orders', 'Damage')
    #UseCaseEventType.create('cust_orders', 'Transfer')
    #UseCaseEventType.create('cust_orders', 'Reciprocal Transfer')
    #UseCaseEventType.create('cust_orders', 'Payment')
    #UseCaseEventType.create('cust_orders', 'Receipt')
    #UseCaseEventType.create('cust_orders', 'Sale')
    #UseCaseEventType.create('cust_orders', 'Shipment')
    #UseCaseEventType.create('purchasing', 'Payment')
    #UseCaseEventType.create('purchasing', 'Receipt')
    #UseCaseEventType.create('res_contr', 'Time Contribution')
    #UseCaseEventType.create('res_contr', 'Resource Contribution')
    #UseCaseEventType.create('purch_contr', 'Time Contribution')
    #UseCaseEventType.create('purch_contr', 'Expense')
    #UseCaseEventType.create('purch_contr', 'Payment')
    #UseCaseEventType.create('purch_contr', 'Receipt')
    #UseCaseEventType.create('exp_contr', 'Time Contribution')
    #UseCaseEventType.create('exp_contr', 'Expense')
    #UseCaseEventType.create('exp_contr', 'Payment')
    #UseCaseEventType.create('sale', 'Shipment')
    #UseCaseEventType.create('sale', 'Cash Receipt')
    #UseCaseEventType.create('sale', 'Time Contribution')
    UseCaseEventType.create('distribution', 'Distribution')
    UseCaseEventType.create('distribution', 'Time Contribution')
    UseCaseEventType.create('distribution', 'Cash Disbursement')
    UseCaseEventType.create('val_equation', 'Time Contribution')
    UseCaseEventType.create('val_equation', 'Resource Production')
    UseCaseEventType.create('payout', 'Payout')
    #UseCaseEventType.create('transfer', 'Transfer')
    #UseCaseEventType.create('transfer', 'Reciprocal Transfer')
    #UseCaseEventType.create('available', 'Make Available')
    #UseCaseEventType.create('intrnl_xfer', 'Transfer')
    #UseCaseEventType.create('intrnl_xfer', 'Reciprocal Transfer')
    #UseCaseEventType.create('intrnl_xfer', 'Time Contribution')
    #UseCaseEventType.create('supply_xfer', 'Transfer')
    #UseCaseEventType.create('supply_xfer', 'Reciprocal Transfer')
    #UseCaseEventType.create('supply_xfer', 'Time Contribution')
    #UseCaseEventType.create('demand_xfer', 'Transfer')
    #UseCaseEventType.create('demand_xfer', 'Reciprocal Transfer')
    #UseCaseEventType.create('demand_xfer', 'Time Contribution')

    print "created use case event type associations"


post_migrate.connect(create_usecase_eventtypes)