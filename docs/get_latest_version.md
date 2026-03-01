```python
BIOPORTAL_BASE = "https://data.bioontology.org"
ONTOLOGY_ACRONYM = "ICD10CM"
API_KEY = ""
URL = f"{BIOPORTAL_BASE}/ontologies/{ONTOLOGY_ACRONYM}/submissions?apikey={apikey}&display_links=false"

```
- The `URL` returns **a list of submissions**. In practice, for ICD10CM we observed length of the list to be 27 (27 releases) (data accessed: Feb 26, 2026).
- The script computes **“latest” explicitly**: it picks the submission with the maximum `released` date (ontology version release); if `released` is missing, it falls back to the maximum `submissionId`. That way we do not depend on API response order.

Example submissions (the script picks the one with max `released`; two entries shown below):
```json
{
  "contact": [
    {
      "id": "https://data.bioontology.org/contacts/4cfd21b0-032b-0131-abbd-001ec9b0ea92",
      "name": "Patricia Brooks",
      "email": "pbrooks@hcfa.gov"
    }
  ],
  "ontology": {
    "administeredBy": [
      "https://data.bioontology.org/users/admin"
    ],
    "acronym": "ICD10CM",
    "name": "International Classification of Diseases, Version 10 - Clinical Modification",
    "@id": "https://data.bioontology.org/ontologies/ICD10CM",
    "@type": "http://data.bioontology.org/metadata/Ontology",
    "@context": {
      "@vocab": "http://data.bioontology.org/metadata/",
      "acronym": "http://omv.ontoware.org/2005/05/ontology#acronym",
      "name": "http://omv.ontoware.org/2005/05/ontology#name",
      "administeredBy": {
        "@id": "http://data.bioontology.org/metadata/User",
        "@type": "@id"
      },
      "@language": "en"
    }
  },
  "hasOntologyLanguage": "UMLS",
  "released": "2024-11-04T00:00:00.000+00:00",
  "creationDate": "2025-01-16T15:48:19.000-08:00",
  "homepage": "https://www.cdc.gov/nchs/icd/icd-10-cm.htm",
  "publication": [
    "http://www.cms.hhs.gov/"
  ],
  "documentation": "http://www.cms.hhs.gov/",
  "version": "CD10CM_2025",
  "description": "International Classification of Diseases, 10th Edition, Clinical Modification",
  "status": "production",
  "submissionId": 27,
  "@id": "https://data.bioontology.org/ontologies/ICD10CM/submissions/27",
  "@type": "http://data.bioontology.org/metadata/OntologySubmission",
  "@context": {
    "@vocab": "http://data.bioontology.org/metadata/",
    "submissionId": "http://data.bioontology.org/metadata/submissionId",
    "version": "http://omv.ontoware.org/2005/05/ontology#version",
    "status": "http://omv.ontoware.org/2005/05/ontology#status",
    "hasOntologyLanguage": "http://omv.ontoware.org/2005/05/ontology#hasOntologyLanguage",
    "description": "http://omv.ontoware.org/2005/05/ontology#description",
    "homepage": "http://xmlns.com/foaf/0.1/homepage",
    "documentation": "http://omv.ontoware.org/2005/05/ontology#documentation",
    "publication": "http://data.bioontology.org/metadata/publication",
    "released": "http://data.bioontology.org/metadata/released",
    "creationDate": "http://omv.ontoware.org/2005/05/ontology#creationDate",
    "contact": "http://data.bioontology.org/metadata/contact",
    "ontology": "http://data.bioontology.org/metadata/ontology",
    "@language": "en"
  }
}
{
  "contact": [
    {
      "id": "https://data.bioontology.org/contacts/4cfd21b0-032b-0131-abbd-001ec9b0ea92",
      "name": "Patricia Brooks",
      "email": "pbrooks@hcfa.gov"
    }
  ],
  "ontology": {
    "administeredBy": [
      "https://data.bioontology.org/users/admin"
    ],
    "acronym": "ICD10CM",
    "name": "International Classification of Diseases, Version 10 - Clinical Modification",
    "@id": "https://data.bioontology.org/ontologies/ICD10CM",
    "@type": "http://data.bioontology.org/metadata/Ontology",
    "@context": {
      "@vocab": "http://data.bioontology.org/metadata/",
      "acronym": "http://omv.ontoware.org/2005/05/ontology#acronym",
      "name": "http://omv.ontoware.org/2005/05/ontology#name",
      "administeredBy": {
        "@id": "http://data.bioontology.org/metadata/User",
        "@type": "@id"
      },
      "@language": "en"
    }
  },
  "hasOntologyLanguage": "UMLS",
  "released": "2024-05-06T00:00:00.000+00:00",
  "creationDate": "2024-08-28T15:51:30.000-07:00",
  "homepage": null,
  "publication": [
    "http://www.cms.hhs.gov/"
  ],
  "documentation": "http://www.cms.hhs.gov/",
  "version": "2024AA",
  "description": "International Classification of Diseases, 10th Edition, Clinical Modification, 2011_01",
  "status": "production",
  "submissionId": 26,
  "@id": "https://data.bioontology.org/ontologies/ICD10CM/submissions/26",
  "@type": "http://data.bioontology.org/metadata/OntologySubmission",
  "@context": {
    "@vocab": "http://data.bioontology.org/metadata/",
    "submissionId": "http://data.bioontology.org/metadata/submissionId",
    "version": "http://omv.ontoware.org/2005/05/ontology#version",
    "status": "http://omv.ontoware.org/2005/05/ontology#status",
    "hasOntologyLanguage": "http://omv.ontoware.org/2005/05/ontology#hasOntologyLanguage",
    "description": "http://omv.ontoware.org/2005/05/ontology#description",
    "homepage": "http://xmlns.com/foaf/0.1/homepage",
    "documentation": "http://omv.ontoware.org/2005/05/ontology#documentation",
    "publication": "http://data.bioontology.org/metadata/publication",
    "released": "http://data.bioontology.org/metadata/released",
    "creationDate": "http://omv.ontoware.org/2005/05/ontology#creationDate",
    "contact": "http://data.bioontology.org/metadata/contact",
    "ontology": "http://data.bioontology.org/metadata/ontology",
    "@language": "en"
  }
}
```
Note: In the BioPortal OntologySubmission payload (see example above, submission 27 with `"version": "CD10CM_2025"`):

- **released** (e.g. `"2024-11-04T00:00:00.000+00:00"` in that example)  
  Is the official release date of that ontology version from the source (e.g. NLM/CMS for ICD-10-CM). It’s when that content version was published, not when BioPortal got it.

- **creationDate** (e.g. `"2025-01-16T15:48:19.000-08:00"` in that example)  
  Is when this submission was created in BioPortal — i.e. when this version was uploaded or registered into BioPortal. So it’s “when it showed up in BioPortal,” not when the ontology was released by the provider.

So we can have `creationDate` after `released`: in the example, the CD10CM_2025 content was released 2024-11-04 and was added to BioPortal on 2025-01-16.

For picking the “latest” submission, **released** is the one that reflects the actual ontology version date; **creationDate** reflects BioPortal’s ingestion time.
