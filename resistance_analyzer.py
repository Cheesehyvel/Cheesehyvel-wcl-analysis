from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
import pprint

class ResistanceAnalyzer:
    def __init__(self, token):
        transport = AIOHTTPTransport(url='https://classic.warcraftlogs.com/api/v2/client', headers={'Authorization': 'Bearer '+token}, timeout=120)
        self.client = Client(transport=transport, fetch_schema_from_transport=True)

    def run(self, zoneID, encounterID, startTime = 0, limit = 10, pages = 1, page = 1, format=None, spellFilter=True):

        data = {}

        query = gql("""
            query ($zoneID: Int!, $encounterID: Int!, $startTime: Float!, $limit: Int!, $page: Int!) {
              reportData {
                reports(zoneID: $zoneID, startTime: $startTime, limit: $limit, page: $page) {
                  data {
                    title
                    events(encounterID: $encounterID, startTime: 0, endTime: 999999999, limit: 20000) {
                       data
                    }
                  }
                }
              }
            }
        """)

        for p in range(page, page+pages):

            result = self.client.execute(query, {
                "zoneID": zoneID,
                "encounterID": encounterID,
                "startTime": startTime,
                "limit": limit,
                "page": p,
            })

            if len(result["reportData"]["reports"]["data"]) < 1:
                break

            for report in result["reportData"]["reports"]["data"]:
                re = self.analyzeReport(report, spellFilter)

                if "total" not in data:
                    data = re
                else:
                    for spell_id in re["spells"]:
                        if spell_id not in data["spells"]:
                            data["spells"][spell_id] = re["spells"][spell_id]
                        else:
                            for index, dataset in enumerate(re["spells"][spell_id]["datasets"]):
                                for key in dataset:
                                    if key != "coe":
                                        data["spells"][spell_id]["datasets"][index][key]+= dataset[key]

                    for index, dataset in enumerate(re["total"]):
                        for key in dataset:
                            if key != "coe":
                                data["total"][index][key]+= dataset[key]

        # Summarize
        if "total" in data:
            for spell_id in data["spells"]:
                for dataset in data["spells"][spell_id]["datasets"]:
                    dataset["mitigation"] = str(round(100 - 100*(dataset["75"] * 0.25 + dataset["50"] * 0.5 + dataset["25"] * 0.75 + dataset["0"])/dataset["count"], 2))+"%"

            for dataset in data["total"]:
                if dataset["count"] > 0:
                    dataset["mitigation"] = str(round(100 - 100*(dataset["75"] * 0.25 + dataset["50"] * 0.5 + dataset["25"] * 0.75 + dataset["0"])/dataset["count"], 2))+"%"

        if format == "csv":
            return self.toCsv(data)

        return data

    def analyzeReport(self, report, spellFilter):
        data = {
            "spells": {},
            "total": [
                {
                    "coe": False,
                    "count": 0,
                    "0": 0,
                    "25": 0,
                    "50": 0,
                    "75": 0
                },
                {
                    "coe": True,
                    "count": 0,
                    "0": 0,
                    "25": 0,
                    "50": 0,
                    "75": 0
                }
            ]
        }

        primarySpells = [27215, 32231, 27209, 27070, 30451, 27074]
        coe_active = False
        coe = 27228

        for event in report["events"]["data"]:
            if event["type"] == "applydebuff" and event["abilityGameID"] == coe:
                coe_active = True

            if event["type"] == "removedebuff" and event["abilityGameID"] == coe:
                coe_active = False

            if (event["type"] == "damage" and
                "tick" not in event and
                "unmitigatedAmount" in event and
                int(event["unmitigatedAmount"]) > 0 and
                event["hitType"] != 6 and
                event["abilityGameID"] != 1 and
                (spellFilter == False or event["abilityGameID"] in primarySpells)):

                if event["abilityGameID"] not in data["spells"]:
                    data["spells"][event["abilityGameID"]] = {
                        "spellName": self.spellName(event["abilityGameID"]),
                        "datasets": [
                            {
                                "coe": False,
                                "count": 0,
                                "0": 0,
                                "25": 0,
                                "50": 0,
                                "75": 0
                            },
                            {
                                "coe": True,
                                "count": 0,
                                "0": 0,
                                "25": 0,
                                "50": 0,
                                "75": 0
                            }
                        ]
                    }

                if "resisted" in event:
                    key = str(round(event["resisted"] / event["unmitigatedAmount"] * 100))
                else:
                    key = "0"

                coe_key = int(coe_active)
                data["spells"][event["abilityGameID"]]["datasets"][coe_key]["count"]+= 1
                data["spells"][event["abilityGameID"]]["datasets"][coe_key][key]+= 1
                data["total"][coe_key]["count"]+= 1
                data["total"][coe_key][key]+= 1

        return data

    def spellName(self, id):
        key = str(id)
        spells = {
            "27215": "Immolate",
            "32231": "Incinerate",
            "27209": "Shadow Bolt",
            "27285": "Seed of Corruption",
            "30546": "Shadowburn",
            "11763": "Firebolt",
            "27072": "Frostbolt",
            "27070": "Fireball",
            "33938": "Pyroblast",
            "30451": "Arcane Blast",
            "27074": "Scorch",
            "10207": "Scorch R7",
            "27079": "Fire Blast",
            "27087": "Cone of Cold",
            "13021": "Blast Wave",
            "30455": "Ice Lance",
            "31707": "Waterbolt",
            "33395": "Freeze",
            "34913": "Molten Armor",
            "27150": "Retribution Aura",
        }
        if key in spells:
            return spells[key]
        return "Unknown "+key;

    def toCsv(self, data, d = "\t"):
        csv = "Spell"+d+"CoE"+d+"Hits"+d+"0%"+d+"25%"+d+"50%"+d+"75%"+d+"Mitigation\n"

        if "total" in data:
            for spell_id in data["spells"]:
                for dataset in data["spells"][spell_id]["datasets"]:
                    csv+= str(data["spells"][spell_id]["spellName"])+d
                    for key in dataset:
                        csv+= str(dataset[key])+d
                    csv = csv[0:-1]+"\n"

            for dataset in data["total"]:
                csv+= "Total"+d
                for key in dataset:
                    csv+= str(dataset[key])+d
                csv = csv[0:-1]+"\n"

        return csv

