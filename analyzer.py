from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
import pprint

class Analyzer:
    def __init__(self, token):
        transport = AIOHTTPTransport(url='https://classic.warcraftlogs.com/api/v2/client', headers={'Authorization': 'Bearer '+token}, timeout=120)
        self.client = Client(transport=transport, fetch_schema_from_transport=True)

    def run(self, zoneID, encounterID, sourceClass, limit = 10, pages = 1, page = 1, format=None, spellFilter=True):

        data = {
            "spells": {},
            "total": {
                "count": 0,
                "0": 0,
                "25": 0,
                "50": 0,
                "75": 0,
            }
        }

        query = gql("""
            query ($zoneID: Int!, $encounterID: Int!, $sourceClass: String!, $limit: Int!, $page: Int!) {
              reportData {
                reports(zoneID: $zoneID, guildServerRegion: "EU", limit: $limit, page: $page) {
                  data {
                    title
                    events(encounterID: $encounterID, sourceClass: $sourceClass, dataType: DamageDone, startTime: 0, endTime: 999999999, limit: 400) {
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
                "sourceClass": sourceClass,
                "limit": limit,
                "page": p,
            })

            if len(result["reportData"]["reports"]["data"]) < 1:
                break

            for report in result["reportData"]["reports"]["data"]:
                re = self.analyzeReport(report, spellFilter)

                for spell_id in re["spells"]:
                    if spell_id not in data["spells"]:
                        data["spells"][spell_id] = re["spells"][spell_id]
                    else:
                        for key in re["spells"][spell_id]:
                            if key != "spellName":
                                data["spells"][spell_id][key]+= re["spells"][spell_id][key]

                for key in re["total"]:
                    data["total"][key]+= re["total"][key]

        # Summarize
        for spell_id in data["spells"]:
            data["spells"][spell_id]["mitigation"] = str(round(100 - 100*(data["spells"][spell_id]["75"] * 0.25 + data["spells"][spell_id]["50"] * 0.5 + data["spells"][spell_id]["25"] * 0.75 + data["spells"][spell_id]["0"])/data["spells"][spell_id]["count"], 2))+"%"

        if data["total"]["count"] > 0:
            data["total"]["mitigation"] = str(round(100 - 100*(data["total"]["75"] * 0.25 + data["total"]["50"] * 0.5 + data["total"]["25"] * 0.75 + data["total"]["0"])/data["total"]["count"], 2))+"%"

        if format == "csv":
            return self.toCsv(data)

        return data

    def analyzeReport(self, report, spellFilter):
        data = {
            "spells": {},
            "total": {
                "count": 0,
                "0": 0,
                "25": 0,
                "50": 0,
                "75": 0
            }
        }

        primarySpells = [27215, 32231, 27209, 27070, 30451, 27074]

        for event in report["events"]["data"]:
            if (event["type"] == "damage" and
                "tick" not in event and
                "sourceMarker" not in event and
                "unmitigatedAmount" in event and
                int(event["unmitigatedAmount"]) > 0 and
                event["hitType"] != 6 and
                event["abilityGameID"] != 1 and
                (spellFilter == False or event["abilityGameID"] in primarySpells)):

                if event["abilityGameID"] not in data["spells"]:
                    data["spells"][event["abilityGameID"]] = {
                        "spellName": self.spellName(event["abilityGameID"]),
                        "count": 0,
                        "0": 0,
                        "25": 0,
                        "50": 0,
                        "75": 0
                    }

                if event["hitType"] == 16:
                    key = str(round(event["resisted"] / event["unmitigatedAmount"] * 100))
                else:
                    key = "0"

                data["spells"][event["abilityGameID"]]["count"]+= 1
                data["total"]["count"]+= 1
                data["spells"][event["abilityGameID"]][key]+= 1
                data["total"][key]+= 1

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
        csv = "Spell"+d+"Hits"+d+"0%"+d+"25%"+d+"50%"+d+"75%"+d+"Mitigation\n"

        for spell_id in data["spells"]:
            for key in data["spells"][spell_id]:
                csv+= str(data["spells"][spell_id][key])+d
            csv = csv[0:-1]+"\n"

        csv+= "Total"+d;
        for key in data["total"]:
            csv+= str(data["total"][key])+d
        csv = csv[0:-1]+"\n"

        return csv

