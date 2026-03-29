import os
import requests
import json

url = "https://api.tfl.gov.uk"
api_key = os.getenv("TFL_API_KEY")

def get_modes():
    modes_url = f"{url}/Line/Meta/Modes"
    modes = requests.get(modes_url).json()
    mode_names = [i["modeName"] for i in modes]
    return mode_names

def get_lines(modes):
    lines_url = f"{url}/Line/Mode/{modes}"
    lines = requests.get(lines_url).json()
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

def generate_json(lines):
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
            "name": line["name"]
        })

    lines_json = {
        "Lines": all_lines,
        "Instances": instances
    }

    with open("data/raw/tfl.json", "w") as f:
        json.dump(lines_json, f, indent=3)

if __name__ == "__main__":
    modes = get_modes()
    modes = ",".join(modes)
    lines = get_lines(modes)
    generate_json(lines)