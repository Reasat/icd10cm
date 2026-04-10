from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


metamodel_version = "1.7.0"
version = "0.1.0"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )





class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'mondo_src',
     'default_range': 'string',
     'description': 'Minimal LinkML schema for a Mondo-ready ontology source. '
                    'Captures only the elements Mondo uses: labels, definitions, '
                    'synonyms, and hierarchical parentage. Used to validate and '
                    'export each source as a schema-conformant YAML + OWL '
                    'artefact.',
     'id': 'https://w3id.org/monarch-initiative/mondo-source-schema',
     'imports': ['linkml:types'],
     'name': 'mondo_source_schema',
     'prefixes': {'ICD10CM': {'prefix_prefix': 'ICD10CM',
                              'prefix_reference': 'http://purl.bioontology.org/ontology/ICD10CM/'},
                  'dcterms': {'prefix_prefix': 'dcterms',
                              'prefix_reference': 'http://purl.org/dc/terms/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'},
                  'mondo_src': {'prefix_prefix': 'mondo_src',
                                'prefix_reference': 'https://w3id.org/monarch-initiative/mondo-source-schema/'},
                  'obo': {'prefix_prefix': 'obo',
                          'prefix_reference': 'http://purl.obolibrary.org/obo/'},
                  'oboInOwl': {'prefix_prefix': 'oboInOwl',
                               'prefix_reference': 'http://www.geneontology.org/formats/oboInOwl#'},
                  'owl': {'prefix_prefix': 'owl',
                          'prefix_reference': 'http://www.w3.org/2002/07/owl#'},
                  'rdfs': {'prefix_prefix': 'rdfs',
                           'prefix_reference': 'http://www.w3.org/2000/01/rdf-schema#'},
                  'skos': {'prefix_prefix': 'skos',
                           'prefix_reference': 'http://www.w3.org/2004/02/skos/core#'}},
     'source_file': '/workspace/Projects/icd10cm/linkml/mondo_source_schema.yaml'} )


class OntologyDocument(ConfiguredBaseModel):
    """
    Top-level container representing a single ontology source release.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'owl:Ontology',
         'from_schema': 'https://w3id.org/monarch-initiative/mondo-source-schema',
         'tree_root': True})

    title: str = Field(default=..., description="""Human-readable title of the ontology source.""", json_schema_extra = { "linkml_meta": {'domain_of': ['OntologyDocument'], 'slot_uri': 'dcterms:title'} })
    version: str = Field(default=..., description="""Version string for this release (e.g. \"2024ab\" or \"2025-03-01\").""", json_schema_extra = { "linkml_meta": {'domain_of': ['OntologyDocument'], 'slot_uri': 'owl:versionInfo'} })
    source: Optional[str] = Field(default=None, description="""Provenance IRI for the upstream ontology file (oboInOwl:source), e.g. BioPortal submission URL.""", json_schema_extra = { "linkml_meta": {'domain_of': ['OntologyDocument'], 'slot_uri': 'oboInOwl:source'} })
    ontology_comment: Optional[str] = Field(default=None, description="""Ontology-level rdfs:comment (e.g. UMLS2RDF tool line).""", json_schema_extra = { "linkml_meta": {'domain_of': ['OntologyDocument'], 'slot_uri': 'rdfs:comment'} })
    version_iri: Optional[str] = Field(default=None, description="""Ontology owl:versionIRI for this build (distinct from versionInfo text).""", json_schema_extra = { "linkml_meta": {'domain_of': ['OntologyDocument'], 'slot_uri': 'owl:versionIRI'} })
    terms: list[OntologyTerm] = Field(default=..., description="""All terms included in this source release.""", json_schema_extra = { "linkml_meta": {'domain_of': ['OntologyDocument']} })


class OntologyTerm(ConfiguredBaseModel):
    """
    A single class / concept from the source ontology, containing only the elements Mondo requires for ingest.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'owl:Class',
         'from_schema': 'https://w3id.org/monarch-initiative/mondo-source-schema'})

    id: str = Field(default=..., description="""Canonical CURIE identifier for the term (e.g. \"ICD10CM:A00\").""", json_schema_extra = { "linkml_meta": {'domain_of': ['OntologyTerm'], 'slot_uri': 'dcterms:identifier'} })
    label: str = Field(default=..., description="""The preferred human-readable label.""", json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl', 'value': 'AnnotationAssertion'}},
         'domain_of': ['OntologyTerm'],
         'slot_uri': 'rdfs:label'} })
    definition: Optional[str] = Field(default=None, description="""Textual definition (IAO:0000115).""", json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl', 'value': 'AnnotationAssertion'}},
         'domain_of': ['OntologyTerm'],
         'recommended': True,
         'slot_uri': 'obo:IAO_0000115'} })
    exact_synonyms: Optional[list[str]] = Field(default=None, description="""Exact-match synonyms (oboInOwl:hasExactSynonym).""", json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl', 'value': 'AnnotationAssertion'}},
         'domain_of': ['OntologyTerm'],
         'recommended': True,
         'slot_uri': 'oboInOwl:hasExactSynonym'} })
    related_synonyms: Optional[list[str]] = Field(default=None, description="""Related synonyms (oboInOwl:hasRelatedSynonym).""", json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl', 'value': 'AnnotationAssertion'}},
         'domain_of': ['OntologyTerm'],
         'slot_uri': 'oboInOwl:hasRelatedSynonym'} })
    narrow_synonyms: Optional[list[str]] = Field(default=None, description="""Narrower synonyms (oboInOwl:hasNarrowSynonym).""", json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl', 'value': 'AnnotationAssertion'}},
         'domain_of': ['OntologyTerm'],
         'slot_uri': 'oboInOwl:hasNarrowSynonym'} })
    broad_synonyms: Optional[list[str]] = Field(default=None, description="""Broader synonyms (oboInOwl:hasBroadSynonym).""", json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl', 'value': 'AnnotationAssertion'}},
         'domain_of': ['OntologyTerm'],
         'slot_uri': 'oboInOwl:hasBroadSynonym'} })
    close_synonyms: Optional[list[str]] = Field(default=None, description="""Close synonyms (skos:closeMatch). oboInOwl has no dedicated close-synonym property, so skos:closeMatch is used as the nearest equivalent.""", json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl', 'value': 'AnnotationAssertion'}},
         'domain_of': ['OntologyTerm'],
         'slot_uri': 'skos:closeMatch'} })
    parents: Optional[list[str]] = Field(default=None, description="""Direct is-a parents. Required unless is_root is true.""", json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl', 'value': 'SubClassOf'}},
         'domain_of': ['OntologyTerm'],
         'slot_uri': 'rdfs:subClassOf'} })
    is_root: Optional[bool] = Field(default=False, description="""True when this term has no named parents and sits at the top of the hierarchy. Relaxes the parents requirement.""", json_schema_extra = { "linkml_meta": {'domain_of': ['OntologyTerm'], 'ifabsent': 'false'} })
    deprecated: Optional[bool] = Field(default=False, description="""True when this term is marked owl:deprecated.""", json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl', 'value': 'AnnotationAssertion'}},
         'domain_of': ['OntologyTerm'],
         'ifabsent': 'false',
         'slot_uri': 'owl:deprecated'} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
OntologyDocument.model_rebuild()
OntologyTerm.model_rebuild()
