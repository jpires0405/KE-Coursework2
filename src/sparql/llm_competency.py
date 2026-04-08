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
                ?operator rdfs:label "Transport for London" .
                ?route lt:operatedBy ?operator ;
                       a gtfs:Route ;
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
        "question": "Which tube lines have the highest average ridership during peak hours, according to the TfL Annual Report?",
        "query": """
            SELECT DISTINCT ?lineName ?ridership
            WHERE {
                ?line a lt:TubeLine ;
                      lt:mentionedInReport lt:tfl_annual_report_2024_25 ;
                      lt:hasRidership ?ridership ;
                      rdfs:label|lt:name ?lineName .
            }
            ORDER BY DESC(?ridership)
            LIMIT 5
        """
    },
    {
        "id": "CQ13",
        "question": "What are the names of all train stations that are wheelchair accessible and have a direct connection to the Elizabeth line?",
        "query": """
            SELECT DISTINCT ?stationName
            WHERE {
                lt:london_elizabeth_line lt:servesStation|lt:hasStop ?station .
                ?station lt:wheelchairAccessible true ;
                         rdfs:label|lt:name ?stationName .
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
        "question": "What are the coordinates of all stops that are within a 1km radius of a wheelchair accessible train station on the Overground line?",
        "query": """
            SELECT DISTINCT ?stationName ?lat ?lon
            WHERE {
                lt:london_overground lt:servesStation|lt:hasStop ?station .
                ?station lt:wheelchairAccessible true ;
                         rdfs:label|lt:name ?stationName ;
                         gtfs:lat ?lat ;
                         gtfs:long ?lon .
            }
        """
    },
    {
        "id": "CQ16",
        "question": "Which transport operators have the most routes with night service, and what are the corresponding route numbers?",
        "query": """
            SELECT ?operatorName (COUNT(?route) AS ?nightRouteCount) (GROUP_CONCAT(?routeName; separator=", ") AS ?routes)
            WHERE {
                ?route lt:hasNightService true ;
                       lt:operatedBy ?operator ;
                       rdfs:label|lt:name ?routeName .
                ?operator rdfs:label|lt:name ?operatorName .
            }
            GROUP BY ?operatorName
            HAVING (COUNT(?route) > 0)
            ORDER BY DESC(?nightRouteCount)
        """
    },
    {
        "id": "CQ17",
        "question": "What is the total number of bus stops that are served by routes operated by multiple transport operators, and which operators are they?",
        "query": """
            SELECT ?stopName (COUNT(DISTINCT ?operator) AS ?operatorCount) (GROUP_CONCAT(DISTINCT ?operatorName; separator=", ") AS ?operators)
            WHERE {
                ?route a gtfs:Route ;
                       lt:operatedBy ?operator ;
                       lt:hasStop|lt:servesStation ?stop .
                ?operator rdfs:label|lt:name ?operatorName .
                ?stop rdfs:label|lt:name ?stopName .
            }
            GROUP BY ?stopName
            HAVING (COUNT(DISTINCT ?operator) > 1)
        """
    },
    {
        "id": "CQ18",
        "question": "Which tram lines have the lowest average ridership during off-peak hours, according to the TfL Annual Report, and what are their corresponding line colours?",
        "query": """
            SELECT DISTINCT ?lineName ?color ?ridership
            WHERE {
                ?line a lt:TramLine ;
                      lt:mentionedInReport lt:tfl_annual_report_2024_25 ;
                      lt:hasRidership ?ridership ;
                      lt:lineColour|schema:color ?color ;
                      rdfs:label|lt:name ?lineName .
            }
            ORDER BY ASC(?ridership)
            LIMIT 5
        """
    },
    {
        "id": "CQ19",
        "question": "What are the names of all places that are served by both a river bus line and a train line?",
        "query": """
            SELECT DISTINCT ?stopName
            WHERE {
                ?riverLine a lt:RiverBusLine ;
                           lt:servesStation|lt:hasStop ?stop .
                ?trainLine a lt:TubeLine ;
                           lt:servesStation|lt:hasStop ?stop .
                ?stop rdfs:label|lt:name ?stopName .
            }
        """
    },
    {
        "id": "CQ20",
        "question": "Which train stations have the most interchanges with other transport lines, and what are the corresponding line names?",
        "query": """
            SELECT ?stationName (COUNT(DISTINCT ?line) AS ?lineCount) (GROUP_CONCAT(DISTINCT ?lineName; separator=", ") AS ?lines)
            WHERE {
                ?line lt:servesStation|lt:hasStop ?station ;
                      rdfs:label|lt:name ?lineName .
                ?station rdfs:label|lt:name ?stationName .
            }
            GROUP BY ?stationName
            HAVING (COUNT(DISTINCT ?line) > 1)
            ORDER BY DESC(?lineCount)
            LIMIT 10
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