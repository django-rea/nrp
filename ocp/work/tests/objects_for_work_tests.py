from django.contrib.auth.models import User
from django.conf import settings

import decimal

from django_rea.valueaccounting.models import \
    AgentType, EconomicAgent, AgentUser, EventType, EconomicResourceType, \
    Unit, AgentResourceRoleType

# It creates the needed initial data to run the work tests:
# admin_user, admin_agent, Freedom Coop agent, FC Membership request agent, ...
def initial_test_data():
    # To see debugging errors in the browser while making changes in the test.
    setattr(settings, 'DEBUG', True)

    # We want to reuse the test db, to be faster (manage.py test --keepdb),
    # so we create the objects only if they are not in test db.
    try:
        admin_user = User.objects.get(username='admin_user')
    except User.DoesNotExist:
        admin_user = User.objects.create_superuser(
            username='admin_user',
            password='admin_passwd',
            email='admin_user@example.com'
        )

    # AgentTypes
    individual_at, c = AgentType.objects.get_or_create(
        name='Individual', party_type='individual', is_context=False)

    project_at, c = AgentType.objects.get_or_create(
        name='Project', party_type='team', is_context=True)

    cooperative_at, c = AgentType.objects.get_or_create(
        name='Cooperative', party_type='organization', is_context=True)

    # EconomicAgent for admin_user related to him/her.
    admin_ea, c = EconomicAgent.objects.get_or_create(name='admin_agent',
        nick='admin_agent', agent_type=individual_at,  is_context=False)

    AgentUser.objects.get_or_create(agent=admin_ea, user=admin_user)

    # EconomicAgent for Freedom Coop
    EconomicAgent.objects.get_or_create(name='Freedom Coop',
        nick='Freedom Coop', agent_type=cooperative_at, is_context=True)

    # EconomicAgent for Memebership Request
    EconomicAgent.objects.get_or_create(name='Membership Requests',
        nick='FC MembershipRequest', agent_type=project_at, is_context=True)

    # EventType for todos
    EventType.objects.get_or_create(name='Todo', label='todo',
        relationship='todo', related_to='agent', resource_effect='=')

    EconomicResourceType.objects.get_or_create(name='something_with_Admin', behavior='work')

    # Manage FairCoin
    FC_unit, c = Unit.objects.get_or_create(unit_type='value', name='FairCoin', abbrev='FairCoin')

    EconomicResourceType.objects.get_or_create(name='FairCoin', unit=FC_unit, unit_of_use=FC_unit,
        value_per_unit_of_use=decimal.Decimal('1.00'), substitutable=True, behavior='dig_acct')

    AgentResourceRoleType.objects.get_or_create(name='Owner', is_owner=True)
    
