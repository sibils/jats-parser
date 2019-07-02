from pymongo import MongoClient
from bson.json_util import dumps

client = MongoClient()
print('one')
db = client['biomed'] # nom de la db
print('two')

# trouver un ou des doc
annotations = db.anapmc2.find({'_id': "PMC4804230"})
print('three')
#annotations = db.anapmc2.find({'_id': {"$in":["22874182","22874181","toto"]}})

wfile = open("test.json","w",encoding="utf-8")
wfile.write(dumps(annotations))
wfile.close()
