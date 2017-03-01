"""Models based on REA

These models are based on the Bill McCarthy's Resource-Event-Agent accounting model:
https://www.msu.edu/~mccarth4/
http://en.wikipedia.org/wiki/Resources,_events,_agents_(accounting_model)

REA is also the basis for ISO/IEC FDIS 15944-4 ACCOUNTING AND ECONOMIC ONTOLOGY
http://global.ihs.com/doc_detail.cfm?item_s_key=00495115&item_key_date=920616

"""


#agent with type info, could create a separate agent app as well as support all of NRP
from django_rea.valueaccounting.models.agent import (
    EconomicAgent,
    AgentUser, #should this be here? not sure how we are separating out the account stuff
    AgentAssociation,
    AgentType,
    AgentAssociationType,
)

#could support a separate app for designs, as well as just what is needed for most of NRP -
#but decided to put exchange here too because eventually we want to have combined
#process and exchange recipes
from django_rea.valueaccounting.models.recipe import (
    EconomicResourceType,
    ResourceClass,
    ResourceTypeSpecialPrice,
    CommitmentType,
    EventType,
    ProcessType,
    ResourceTypeList,
    ResourceTypeListElement,
    Feature,
    Option,
    SelectedOption, #double check this is part of options
    Unit,
    ExchangeType,
    TransferType,
)

#could support a resource sharing app, as well as part of the core layer of NRP
from django_rea.valueaccounting.models.resource import (
    EconomicResource,
    ResourceState,
    AgentResourceRole,
    AgentResourceType,
    AgentResourceRoleType,
)

#could combine this and process and exchange - but I think on the view/templace
#side it is good to separate process and exchange
from django_rea.valueaccounting.models.event import (
    EconomicEvent,
    CachedEventSummary,
    EventSummary,
    AccountingReference,
)

from django_rea.valueaccounting.models.process import (
    Process,
)

from django_rea.valueaccounting.models.trade import (
    Exchange,
    Transfer,
)

from django_rea.valueaccounting.models.schedule import (
    Commitment,
    Reciprocity, #possibly not used?
    Order,
)

#only needed if you are doing contributory accounting
from django_rea.valueaccounting.models.distribution import (
    Distribution,
    DistributionValueEquation,
    ValueEquation,
    ValueEquationBucket,
    ValueEquationBucketRule,
    IncomeEventDistribution,
    Claim,
    ClaimEvent,
)

#both process and exchange facet-value config
from django_rea.valueaccounting.models.facetconfig import (
    Facet,
    FacetValue,
    ResourceTypeFacetValue,
    PatternFacetValue,
    ProcessPattern,
    PatternUseCase,
    TransferTypeFacetValue,
    UseCase, #this may need to go somewhere more general, but I think this is most if not all of its usage
    UseCaseEventType,
)

#needed in both agent and resource
from django_rea.valueaccounting.models.location import (
    Location,
)

from django_rea.valueaccounting.models.misc import (
    HomePageLayout,
    Help,
)