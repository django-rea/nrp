from django_rea.valueaccounting.models.recipe import EconomicResourceType
from django_rea.valueaccounting.models.facetconfig import ResourceTypeFacetValue


def select_resource_types(facet_values):
    """ Logic:
        Facet values in different Facets are ANDed.
        Ie, a resource type must have all of those facet values.
        Facet values in the same Facet are ORed.
        Ie, a resource type must have at least one of those facet values.
    """
    # import pdb; pdb.set_trace()
    fv_ids = [fv.id for fv in facet_values]
    rt_facet_values = ResourceTypeFacetValue.objects.filter(facet_value__id__in=fv_ids)
    rts = [rtfv.resource_type for rtfv in rt_facet_values]
    answer = []
    singles = []  # Facets with only one facet_value in the Pattern
    multis = []  # Facets with more than one facet_value in the Pattern
    aspects = {}
    for fv in facet_values:
        if fv.facet not in aspects:
            aspects[fv.facet] = []
        aspects[fv.facet].append(fv)
    for facet, facet_values in aspects.items():
        if len(facet_values) > 1:
            for fv in facet_values:
                multis.append(fv)
        else:
            singles.append(facet_values[0])
    single_ids = [s.id for s in singles]
    # import pdb; pdb.set_trace()
    for rt in rts:
        rt_singles = [rtfv.facet_value for rtfv in rt.facets.filter(facet_value_id__in=single_ids)]
        rt_multis = [rtfv.facet_value for rtfv in rt.facets.exclude(facet_value_id__in=single_ids)]
        if set(rt_singles) == set(singles):
            if not rt in answer:
                if multis:
                    # if multis intersect
                    if set(rt_multis) & set(multis):
                        answer.append(rt)
                else:
                    answer.append(rt)
    answer_ids = [a.id for a in answer]
    return list(EconomicResourceType.objects.filter(id__in=answer_ids))
