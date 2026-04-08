from rdflib import Graph

g = Graph()

g.parse("src/sparql/final_submission_kg.ttl", format="turtle")


PREFIXES = """
    PREFIX gtfs: <http://vocab.gtfs.org/terms#>
    PREFIX lt: <http://example.org/london-transport#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX schema: <https://schema.org/>
"""

competency_questions = [
    {
        "id": "CQ1",
        "question": "What transport operators are in this ontology?",
        "query": """
            SELECT DISTINCT ?operatorName
            WHERE {
                ?operator a lt:TransportOperator ;
                          rdfs:label|lt:name ?operatorName .
            }
        """
    },
    {
        "id": "CQ2",
        "question": "Names of all tube lines available",
        "query": """
            SELECT DISTINCT ?lineName
            WHERE {
                ?line a lt:TubeLine ;
                      rdfs:label|lt:name ?lineName .
            }
        """
    },
    {
        "id": "CQ3",
        "question": "Which stations are served by the Piccadilly line?",
        "query": """
            SELECT DISTINCT ?stationName
            WHERE {
                lt:piccadilly_line lt:servesStation|lt:hasStop ?station .
                ?station rdfs:label|lt:name ?stationName .
            }
        """
    },
    {
        "id": "CQ4",
        "question": "Which bus routes are operated by 'National Express'?",
        "query": """
            SELECT DISTINCT ?routeName
            WHERE {
                ?operator rdfs:label "National Express" .
                ?route lt:operatedBy ?operator ;
                       rdfs:label|lt:name ?routeName .
            }
        """
    },
    {
        "id": "CQ5",
        "question": "Which stops are located in Wandsworth?",
        "query": """
            SELECT DISTINCT ?stopName
            WHERE {
                ?stop lt:locatedIn lt:wandsworth .
                ?stop rdfs:label|lt:name ?stopName .
            }
        """
    },
    {
        "id": "CQ6",
        "question": "What are the operational dates for 'Service 33'?",
        "query": """
            SELECT ?startDate ?endDate
            WHERE {
                lt:service_33 a gtfs:Service ;
                              lt:startDate ?startDate ;
                              lt:endDate ?endDate .
            }
        """
    },
    {
        "id": "CQ7",
        "question": "Which routes are mentioned in the TFL Annual Report?",
        "query": """
            SELECT DISTINCT ?routeName
            WHERE {
                ?route a gtfs:Route ;
                       lt:mentionedInReport lt:tfl_annual_report_2024_25 ;
                       rdfs:label|lt:name ?routeName .
            }
        """
    },
    {
        "id": "CQ8",
        "question": "Find the Coordinates of 'Plaistow Green'",
        "query": """
            SELECT ?lat ?lon
            WHERE {
                ?stop rdfs:label "Plaistow Green" ;
                      gtfs:lat ?lat ;
                      gtfs:long ?lon .
            }
        """
    },
    {
        "id": "CQ9",
        "question": "Which stops are wheelchair accessible?",
        "query": """
            SELECT DISTINCT ?stopName
            WHERE {
                ?stop lt:wheelchairAccessible true ;
                      rdfs:label|lt:name ?stopName .
            }
        """
    },
    {
        "id": "CQ10",
        "question": "Which lines have night service?",
        "query": """
            SELECT DISTINCT ?lineName
            WHERE {
                ?line lt:hasNightService true ;
                      rdfs:label|lt:lineName ?lineName .
            }
        """
    }
]

if __name__ == "__main__":
    for cq in competency_questions:
        print(f"Executing {cq['id']}: {cq['question']}")
        results = g.query(PREFIXES + cq["query"])

        if len(results) == 0:
            print("  -> No results found.")
        else:
            for row in results:
            
                result_dict = row.asdict()
                
                output_parts = []
                for var_name, var_value in result_dict.items():

                    clean_value = str(var_value).split("/")[-1].split("#")[-1]
                    output_parts.append(f"{var_name}: {clean_value}")
                    
                print(f"  -> " + " | ".join(output_parts))
                
        print("-" * 50)