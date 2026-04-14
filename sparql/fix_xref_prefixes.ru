PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>

DELETE { ?s oboInOwl:hasDbXref ?old }
INSERT { ?s oboInOwl:hasDbXref ?new }
WHERE {
  ?s oboInOwl:hasDbXref ?old .
  BIND(
    IF(STRSTARTS(STR(?old), "ICD-11:"),  CONCAT("ICD11:",   SUBSTR(STR(?old), 8)),
    IF(STRSTARTS(STR(?old), "ICD-10:"),  CONCAT("ICD10:",   SUBSTR(STR(?old), 8)),
    IF(STRSTARTS(STR(?old), "MeSH:"),    CONCAT("MESH:",    SUBSTR(STR(?old), 6)),
    IF(STRSTARTS(STR(?old), "OMIM:PS"),  CONCAT("OMIMPS:",  SUBSTR(STR(?old), 8)),
       STR(?old)))))
    AS ?new
  )
  FILTER(?old != ?new)
}
