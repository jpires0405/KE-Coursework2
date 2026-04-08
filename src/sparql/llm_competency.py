from rdflib import Graph

g = Graph()

g.parse("data/kg/final_submission_kg.ttl", format="turtle")


PREFIXES = """
    PREFIX gtfs: <http://vocab.gtfs.org/terms#>
    PREFIX lt: <http://example.org/london-transport#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX schema: <https://schema.org/>
"""

llm_competency_questions = [
    {
        "id": "CQ11",
        "question": "What are the most frequently served stations by bus routes operated by Transport for London?",
        "query": """
            SELECT ?stationName (COUNT(?route) AS ?routeCount)
            WHERE {
                ?route a gtfs:Route ;
                       lt:operatedBy lt:tfl ;
                       lt:servesStation|lt:hasStop ?station .
                ?station rdfs:label|lt:name ?stationName .
            }
            GROUP BY ?stationName
            ORDER BY DESC(?routeCount)
            LIMIT 10
        """
    },
    {
        "id": "CQ12",
        "question": "Which bus routes have the highest frequency according to the TfL Annual Report?",
        "query": """
            SELECT ?routeName ?frequency
            WHERE {
                ?route a gtfs:Route ;
                       lt:mentionedInReport lt:tfl_annual_report_2024_25 ;
                       lt:hasFrequency ?frequency ;
                       rdfs:label|lt:name ?routeName .
            }
            ORDER BY DESC(?frequency)
            LIMIT 10
        """
    },
    {
        "id": "CQ13",
        "question": "Which transport operators have routes that are both mentioned in the report and have a frequency value?",
        "query": """
            SELECT DISTINCT ?operatorName
            WHERE {
                ?route a gtfs:Route ;
                       lt:mentionedInReport lt:tfl_annual_report_2024_25 ;
                       lt:hasFrequency ?frequency ;
                       lt:operatedBy ?operator .
                ?operator rdfs:label|lt:name ?operatorName .
            }
        """
    },
    {
        "id": "CQ14",
        "question": "Which bus routes have the highest frequency of service and are mentioned in the TfL Annual Report as having improved reliability?",
        "query": """
            SELECT DISTINCT ?routeName ?frequency
            WHERE {
                ?route a gtfs:Route ;
                       lt:mentionedInReport lt:tfl_annual_report_2024_25 ;
                       lt:hasFrequency ?frequency ;
                       rdfs:label|lt:name ?routeName .
            }
            ORDER BY DESC(?frequency)
            LIMIT 10
        """
    },
    {
        "id": "CQ15",
        "question": "List all bus stops that are not wheelchair accessible but share a name with an interchange station.",
        "query": """
            SELECT DISTINCT ?busStopName ?interchangeName
            WHERE {
                ?interchange a lt:Interchange ;
                             rdfs:label|lt:name ?interchangeName .
                ?busStop a lt:BusStop ;
                         lt:wheelchairAccessible false ;
                         rdfs:label|lt:name ?busStopName .
                FILTER(CONTAINS(LCASE(?busStopName), LCASE(?interchangeName)))
            }
        """
    },
    {
        "id": "CQ16",
        "question": "Which routes are mentioned in the TfL Annual Report and are operated by an operator that also operates a tube line?",
        "query": """
            SELECT DISTINCT ?routeName ?operatorName ?tubeLineName
            WHERE {
                ?route a gtfs:Route ;
                       lt:mentionedInReport lt:tfl_annual_report_2024_25 ;
                       lt:operatedBy ?operator ;
                       rdfs:label|lt:name ?routeName .
                ?tubeLine a lt:TubeLine ;
                          lt:operatedBy ?operator ;
                          rdfs:label|lt:name ?tubeLineName .
                ?operator rdfs:label|lt:name ?operatorName .
            }
        """
    },
    {
        "id": "CQ17",
        "question": "Which bus services are active during the Easter weekend of 2026 (April 4–5, 2026)?",
        "query": """
            SELECT DISTINCT ?serviceId ?startDate ?endDate
            WHERE {
                ?service a gtfs:Service ;
                         lt:startDate ?startDate ;
                         lt:endDate ?endDate .
                FILTER(?startDate <= "20260405" && ?endDate >= "20260404")
                BIND(STR(?service) AS ?serviceId)
            }
        """
    },
    {
        "id": "CQ18",
        "question": "Which transport lines are currently experiencing disruptions, and what are the explicitly stated reasons for these disruptions?",
        "query": """
            SELECT ?lineName ?reason
            WHERE {
                ?line a/rdfs:subClassOf* lt:TransportLine ;
                      lt:isDisrupted true ;
                      lt:disruptionReason ?reason ;
                      schema:name|lt:lineName|rdfs:label ?lineName .
            }
            ORDER BY ?lineName
        """
    },
    {
        "id": "CQ19",
        "question": "What are the names of train stations that are interchanges (lt:Interchange) between at least three different transport lines, and which lines are they?",
        "query": """
            SELECT ?stationName (GROUP_CONCAT(DISTINCT ?lineName; separator=", ") AS ?lines)
            WHERE {
                ?station a lt:Interchange ;
                         rdfs:label|lt:name ?stationName .
                ?line lt:servesStation|lt:hasStop ?station ;
                      rdfs:label|lt:name ?lineName .
            }
            GROUP BY ?stationName
            HAVING (COUNT(DISTINCT ?line) >= 3)
            ORDER BY DESC(COUNT(DISTINCT ?line))
        """
    },
    {
        "id": "CQ20",
        "question": "What are the names of all transport operators that operate bus routes, and how many distinct bus routes does each operator manage?",
        "query": """
            SELECT ?operatorName (COUNT(DISTINCT ?route) AS ?routeCount)
            WHERE {
                ?operator a lt:TransportOperator ;
                          schema:name|lt:operatorName|rdfs:label ?operatorName .
                          
                ?route a lt:BusRoute ;
                       lt:operatedBy ?operator .
            }
            GROUP BY ?operatorName
            ORDER BY DESC(?routeCount)
        """
    }
]

for cq in llm_competency_questions:
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