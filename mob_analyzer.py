from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
import pprint

class MobAnalyzer:
    def __init__(self, token):
        transport = AIOHTTPTransport(url='https://classic.warcraftlogs.com/api/v2/client', headers={'Authorization': 'Bearer '+token}, timeout=120)
        self.client = Client(transport=transport, fetch_schema_from_transport=True)

    def run(self, code, raid="naxx", format=None):

        requirements = self.mobRequirements(raid)
        if requirements == None:
            print("Invalid raid")
            return None

        query = gql("""
            query($code: String!) {
                reportData {
                    report(code: $code) {
                        events(startTime: 0, endTime: 9999999999, hostilityType: Enemies, dataType: Deaths, limit: 10000) {
                            data
                        }
                        masterData {
                            actors(type: "npc") {
                                id
                                gameID
                                name
                            }
                        }
                    }
                }
            }
        """)

        result = self.client.execute(query, {
            "code": code
        })

        mobs = {}
        idmap = {}

        for actor in result["reportData"]["report"]["masterData"]["actors"]:
            idmap[actor["id"]] = actor["gameID"]
            mobs[actor["gameID"]] = actor
            mobs[actor["gameID"]]["deaths"] = 0

        for event in result["reportData"]["report"]["events"]["data"]:
            if event["targetID"] in idmap:
                mobs[idmap[event["targetID"]]]["deaths"]+= 1

        for req in requirements:
            req["deaths"] = 0
            for mobID in req["ids"]:
                if mobID not in mobs:
                    req["name"] = "Unknown"
                    break
                if "name" not in req:
                    req["name"] = mobs[mobID]["name"]
                else:
                    req["name"]+= " / "+mobs[mobID]["name"]
                req["deaths"]+= mobs[mobID]["deaths"]
            if req["min"] > req["deaths"]:
                req["missing"] = req["min"] - req["deaths"]
                req["time"] = 300 / req["min"] * req["missing"]
            else:
                req["missing"] = 0
                req["time"] = 0

        requirements = sorted(requirements, key=lambda i: i["name"])

        if format == "csv":
            return self.toCsv(requirements)

        return requirements

    def toCsv(self, data, d = "\t"):
        csv = "Mob(s)"+d+"Required"+d+"Killed"+d+"Missing"+d+"Time penalty\n"

        for req in data:
            csv+= req["name"]+d
            csv+= str(req["min"])+d
            csv+= str(req["deaths"])+d
            csv+= str(req["missing"])+d
            csv+= str(req["time"])+"\n"

        return csv

    def mobRequirements(self, raid):
        req = []

        if raid == "naxx":
            req.append({"ids": [15977], "min": 110})
            req.append({"ids": [15976], "min": 10})
            req.append({"ids": [15974], "min": 22})
            req.append({"ids": [15975], "min": 21})
            req.append({"ids": [15978], "min": 1})
            req.append({"ids": [15980,15981], "min": 32})
            req.append({"ids": [15979], "min": 4})
            req.append({"ids": [16018,16029], "min": 11})
            req.append({"ids": [16024], "min": 20})
            req.append({"ids": [16021], "min": 3})
            req.append({"ids": [16020], "min": 12})
            req.append({"ids": [16022], "min": 15})
            req.append({"ids": [16025], "min": 7})
            req.append({"ids": [30071], "min": 3})
            req.append({"ids": [30083], "min": 10})
            req.append({"ids": [16145], "min": 15})
            req.append({"ids": [16146], "min": 24})
            req.append({"ids": [16156], "min": 22})
            req.append({"ids": [16193], "min": 4})
            req.append({"ids": [16164], "min": 5})
            req.append({"ids": [16165], "min": 6})
            req.append({"ids": [16163], "min": 13})
            req.append({"ids": [16194,16215,16216], "min": 10})
            req.append({"ids": [16168], "min": 6})
            req.append({"ids": [16243], "min": 6})
            req.append({"ids": [16244], "min": 9})
            req.append({"ids": [16034], "min": 2})
            req.append({"ids": [16036], "min": 10})
            req.append({"ids": [16037], "min": 10})
            req.append({"ids": [16236, 16056, 16057], "min": 20})

        else:
            return None

        return req
