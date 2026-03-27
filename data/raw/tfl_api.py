import os
import requests
import json

url = "https://api.tfl.gov.uk"
api_key = os.getenv("TFL_API_KEY")
params = {"app_key": api_key} if api_key else {}

def get_modes():
    modes_url = f"{url}/Line/Meta/Modes"
    modes = requests.get(modes_url, params=params).json()
    mode_names = [i["modeName"] for i in modes]
    return mode_names

def get_lines(modes):
    lines_url = f"{url}/Line/Mode/{modes}"
    lines = requests.get(lines_url, params=params).json()
    return lines

def get_bus_category(name):
    special = {
        "SL": "SuperLoop",
        "N": "NightBus",
        "EL": "EastLondon",
        "SCS": "CycleShuttle",
        "X": "Express"
    }

    geo = {
        "A": "Airport",
        "B": "Bexley",
        "C": "Central",
        "D": "Docklands",
        "E": "Ealing",
        "H": "HarrowHounslow",
        "K": "Kingston",
        "P": "Peckham",
        "R": "RichmondOrpington",
        "S": "Sutton",
        "U": "Uxbridge",
        "W": "WoodGreenWaltham"
    }

    for i, j in special.items():
        if name.startswith(i):
            return j
        
    if name[0] in geo:
        return geo[name[0]]
    
    if name.isdigit():
        num = int(name)
        if 600 <= num <= 699:
            return "SchoolService"
        if 700 <= num <= 899:
            return "RegionalBus"
        return "NormalBus"
    return "OtherBus"

def get_last_stops():
    regular_routes_url = f"{url}/Line/Route?serviceTypes=Regular"
    night_routes_url = f"{url}/Line/Route?serviceTypes=Night"

    regular_routes = requests.get(regular_routes_url, params=params).json()
    night_routes = requests.get(night_routes_url, params=params).json()

    night_last_stops = {}
    for i in night_routes:
        last_stop = {k["destinationName"] for k in i["routeSections"]}
        night_last_stops[i["id"]] = list(last_stop)

    last_stops = {}
    for i in regular_routes:
        line_id = i["id"]
        regular_last_stop = {k["destinationName"] for k in i["routeSections"]}
        night_last_stop = night_last_stops.get(line_id, [])
        last_stops[line_id] = {"Regular": list(regular_last_stop), "Night": night_last_stop}
    return last_stops

def get_all_ids():
    id_url = f"{url}/Line/Route"
    data = requests.get(id_url, params=params).json()
    all_ids = [line['id'] for line in data]
    return all_ids

def get_line_status(modes):
    status_url = f"{url}/Line/Mode/{modes}/Status?detail=true"
    status = requests.get(status_url, params=params).json()

    status_dict = {}
    for line in status:
        disruptions = []
        for d in line["disruptions"]:
            disruptions.append(d.get("description", ""))

        status_dict[line["id"]] = {
            "statusDescription": line["lineStatuses"][0]["statusSeverityDescription"],
            "reason": line["lineStatuses"][0].get("reason", ""),
            "disruptions": disruptions
        }

    return status_dict

def generate_json(lines, last_stops, disruptions):
    all_lines = {
        "TrainLines": [],
        "BusLines": [],
        "RiverLines": [],
        "OtherLines": []
    }
    instances = []

    for line in lines:
        mode = line["modeName"]
        if mode in ["tube", "dlr", "overground", "elizabeth-line", "tram", "national-rail"]:
            category = "TrainLines"
            sub_class = mode
        elif mode == "bus":
            category = "BusLines"
            sub_class = get_bus_category(line["name"])
        elif mode == "river-bus":
            category = "RiverLines"
            sub_class = mode
        else:
            category = "OtherLines"
            sub_class = mode

        if sub_class not in all_lines[category]:
            all_lines[category].append(sub_class)

        instances.append({
            "id": line["id"],
            "belongsToClass": sub_class,
            "name": line["name"],
            "haslastStop": last_stops[line["id"]],
            "disruptions": disruptions[line["id"]]
        })

    lines_json = {
        "Lines": all_lines,
        "Instances": instances
    }

    with open("tfl.json", "w") as f:
        json.dump(lines_json, f, indent=3)

if __name__ == "__main__":
    modes = get_modes()
    modes = ",".join(modes)
    lines = get_lines(modes)
    disruptions = get_line_status(modes)
    last_stops = get_last_stops()
    generate_json(lines, last_stops, disruptions)