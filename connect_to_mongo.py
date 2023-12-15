from pymongo import MongoClient

client = MongoClient(host="candy.lan.text-analytics.ch", port=27017)
db = client["sibils_3_3"]
col = db["pmc23_v3.3.3"]
obj = col.find_one({'_id': 'PMC4909023'}, no_cursor_timeout=True)
for k in obj:
    print(k)

client.close()

