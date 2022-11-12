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
                            for key in re["spells"][spell_id]["dataset"]:
                                data["spells"][spell_id]["dataset"][key]+= re["spells"][spell_id]["dataset"][key]

                    for key in re["total"]:
                        data["total"][key]+= re["total"][key]

        # Summarize
        if "total" in data:
            for spell_id in data["spells"]:
                factor = 0
                for key in data["spells"][spell_id]["dataset"]:
                    if key != "count":
                        factor+= (1.0 - float(key)/100) * data["spells"][spell_id]["dataset"][key]
                data["spells"][spell_id]["dataset"]["mitigation"] = str(round(100 - 100*factor/data["spells"][spell_id]["dataset"]["count"], 2))

            if data["total"]["count"] > 0:
                factor = 0
                for key in data["total"]:
                    if key != "count":
                        factor+= (1.0 - float(key)/100) * data["total"][key]
                data["total"]["mitigation"] = str(round(100 - 100*factor/data["total"]["count"], 2))

        if format == "csv":
            return self.toCsv(data)

        return data

    def analyzeReport(self, report, spellFilter):
        data = {
            "spells": {},
            "total": {
                "count": 0,
                "0": 0,
                "10": 0,
                "20": 0,
                "30": 0,
                "40": 0,
                "50": 0,
                "60": 0,
                "70": 0,
                "80": 0,
                "90": 0
            }
        }

        primarySpells = [42897, 42845, 47610, 42833, 42842, 47809]

        for event in report["events"]["data"]:
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
                        "dataset": {
                            "count": 0,
                            "0": 0,
                            "10": 0,
                            "20": 0,
                            "30": 0,
                            "40": 0,
                            "50": 0,
                            "60": 0,
                            "70": 0,
                            "80": 0,
                            "90": 0
                        }
                    }

                if "resisted" in event:
                    key = str(round(event["resisted"] / event["unmitigatedAmount"] * 100))
                else:
                    key = "0"

                data["spells"][event["abilityGameID"]]["dataset"]["count"]+= 1
                data["spells"][event["abilityGameID"]]["dataset"][key]+= 1
                data["total"]["count"]+= 1
                data["total"][key]+= 1

        return data

    def spellName(self, id):
        key = str(id)
        spells = {
            "42897": "Arcane Blast",
            "42845": "Arcane Missiles",
            "47610": "Frostfire Bolt",
            "42833": "Fireball",
            "42842": "Frostbolt",
            "47809": "Shadow Bolt",
        }
        if key in spells:
            return spells[key]
        return "Unknown "+key;

    def toCsv(self, data, d = "\t"):
        csv = "Spell"+d+"Hits"+d+"0%"+d+"10%"+d+"20%"+d+"30%"+d+"40%"+d+"50%"+d+"60%"+d+"70%"+d+"80%"+d+"90%"+d+"Mitigation\n"

        if "total" in data:
            for spell_id in data["spells"]:
                csv+= str(data["spells"][spell_id]["spellName"])+d
                for key in data["spells"][spell_id]["dataset"]:
                    csv+= str(data["spells"][spell_id]["dataset"][key])+d
                csv = csv[0:-1]+"\n"

            csv+= "Total"+d
            for key in data["total"]:
                csv+= str(data["total"][key])+d
            csv = csv[0:-1]+"\n"

        return csv

