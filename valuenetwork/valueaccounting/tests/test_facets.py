import datetime
from decimal import *

from django.test import TestCase
from django.test import Client

from valuenetwork.valueaccounting.models import *

class FacetTest(TestCase):

    """Testing Facets and ProcessPatterns 

        and ResourceType-Pattern FacetValue matching.

    """

    def setUp(self):

        self.domain = Facet(
            name="Domain",
        )
        self.domain.save()

        self.source = Facet(
            name="Source",
        )
        self.source.save()

        optical_domain = FacetValue(
            facet=self.domain,
            value="Optical"
        )
        optical_domain.save()

        electronic_domain = FacetValue(
            facet=self.domain,
            value="Electronical"
        )
        electronic_domain.save()

        source_us = FacetValue(
            facet=self.source,
            value="Us"
        )
        source_us.save()

        source_them = FacetValue(
            facet=self.source,
            value="Them"
        )
        source_them.save()

        self.optical_pattern = ProcessPattern(
            name="Optics",
        )
        self.optical_pattern.save()

        self.electronic_pattern = ProcessPattern(
            name="Electronics",
        )
        self.electronic_pattern.save()

        self.electroptical_pattern = ProcessPattern(
            name="electro optical",
        )
        self.electroptical_pattern.save()

        self.twofacet_pattern = ProcessPattern(
            name="Two facets",
        )
        self.twofacet_pattern.save()

        self.event_type = EventType(
            name="Production",
            label="produces",
            relationship="out",
            resource_effect="+",
        )
        self.event_type.save()

        pfv = PatternFacetValue(
            pattern=self.optical_pattern,
            facet_value=optical_domain,
            event_type=self.event_type,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.electronic_pattern,
            facet_value=electronic_domain,
            event_type=self.event_type,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.electroptical_pattern,
            facet_value=electronic_domain,
            event_type=self.event_type,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.electroptical_pattern,
            facet_value=optical_domain,
            event_type=self.event_type,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.twofacet_pattern,
            facet_value=electronic_domain,
            event_type=self.event_type,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.twofacet_pattern,
            facet_value=optical_domain,
            event_type=self.event_type,
        )
        pfv.save()

        pfv = PatternFacetValue(
            pattern=self.twofacet_pattern,
            facet_value=source_us,
            event_type=self.event_type,
        )
        pfv.save()

        self.optical_product = EconomicResourceType(
             name="Optical",
        )
        self.optical_product.save()

        self.electronic_product = EconomicResourceType(
             name="Electronic",
        )
        self.electronic_product.save()

        self.twofacet_product = EconomicResourceType(
             name="Two facets",
        )
        self.twofacet_product.save()

        self.other_product = EconomicResourceType(
             name="Other",
        )
        self.other_product.save()

        rtfv = ResourceTypeFacetValue(
            resource_type=self.optical_product,
            facet_value=optical_domain,
        )
        rtfv.save()

        rtfv = ResourceTypeFacetValue(
            resource_type=self.electronic_product,
            facet_value=electronic_domain,
        )
        rtfv.save()

        rtfv = ResourceTypeFacetValue(
            resource_type=self.twofacet_product,
            facet_value=electronic_domain,
        )
        rtfv.save()

        rtfv = ResourceTypeFacetValue(
            resource_type=self.twofacet_product,
            facet_value=source_us,
        )
        rtfv.save()

        
    def test_facet_values(self):
        value_list = self.source.value_list()
        self.assertEqual(value_list, u'Them, Us')

    def test_optical_pattern_resource_types(self):
        rts = self.optical_pattern.get_resource_types(self.event_type)
        self.assertEqual(rts.count(), 1)
        self.assertEqual(rts[0], self.optical_product)

    def test_electronic_pattern_resource_types(self):
        rts = self.electronic_pattern.get_resource_types(self.event_type)
        self.assertEqual(rts.count(), 2)
        self.assertEqual(rts[0], self.electronic_product)
        self.assertEqual(rts[1], self.twofacet_product)

    def test_electroptical_pattern_resource_types(self):
        """Pattern-ResourceType FacetValue matching rules:

            If a Pattern has more than one FacetValue in the same Facet,
            for a ResourceType to match, it must match one of the FacetValues 
            in that same Facet.
            So in this case:
            The electroptical_pattern has the following FacetValues:
                Domain: Electronic
                Domain: Optical
            So the electronic, optical and twofacet_products all match.
            The fact that the twofacet_product has another facet does not matter.
            
        """
        rts = self.electroptical_pattern.get_resource_types(self.event_type)
        self.assertEqual(rts.count(), 3)
        self.assertEqual(rts[0], self.electronic_product)
        self.assertEqual(rts[1], self.optical_product)
        self.assertEqual(rts[2], self.twofacet_product)

    def test_twofacet_pattern_resource_types(self):
        """Pattern-ResourceType FacetValue matching rules:

            If a Pattern has FacetValues in more than one different Facet,
            for a ResourceType to match, it must have FacetValues
            in each of the Facets in the Pattern, 
            and its FacetValues must match one of the FacetValues 
            in the same Facet in the Pattern.
            So in this case:
            The twofacet_pattern has the following FacetValues:
                Domain: Electronic
                Source: Us
            So only the twofacet_product matches.
            
        """
        rts = self.twofacet_pattern.get_resource_types(self.event_type)
        self.assertEqual(rts.count(), 1)
        self.assertEqual(rts[0], self.twofacet_product)

    def test_event_type_for_resource_type(self):
        et = self.electronic_pattern.base_event_type_for_resource_type(
            "out",
            self.electronic_product)
        self.assertEqual(et, self.event_type)

    def test_no_event_type_for_resource_type(self):
        et = self.electronic_pattern.base_event_type_for_resource_type(
            "out",
            self.other_product)
        self.assertEqual(et, None)

        
        
        

