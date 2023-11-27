from pymongo import MongoClient
from pmca_formatter import PmcaFormatter

class MongoPamFetcher:

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def __init__(self, host="localhost", port=27017, db_name="sibils_v3_1"):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        if host is not None and port is not None and db_name is not None:
            client = MongoClient(host=host, port=port)
            self.mongo_db = client[db_name]
        else:
            print("Init MongoPamFetcher without mongo connection")

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def set_collections(self, bibcol_name = "pmcbib23", anacol_name = "pmcana23", sencol_name = "pmcsen23"):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        self.bibcol_name = bibcol_name
        self.anacol_name = anacol_name
        self.sencol_name = anacol_name
        self.bibcol = self.mongo_db[bibcol_name]
        self.anacol = self.mongo_db[anacol_name]
        self.sencol = self.mongo_db[sencol_name]
        
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def fetch_v3_data(self, pmcid):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        obj = self.bibcol.find_one({'_id': pmcid}, no_cursor_timeout=True)
        ana = self.anacol.find_one({'_id': pmcid}, no_cursor_timeout=True)
        sen = self.sencol.find_one({'_id': pmcid}, no_cursor_timeout=True)
        obj["annotations"] = ana["annotations"]
        obj["sentences"] = sen["sentences"]
        return obj


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
if __name__ == '__main__':
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    pmc_list = ["PMC2828183","PMC3082999","PMC3211372","PMC3284193"]

    # init mongo db connection and collections to be fetched
    mongo_pam_fetcher = MongoPamFetcher(host="denver.lan.text-analytics.ch", port=27017, db_name= "sibils_v3_1")
    print("Init done")
    mongo_pam_fetcher.set_collections(bibcol_name = "pmcbib23", anacol_name="pmcana23", sencol_name="pmcsen23" )
    print("Collections set")

    # get an object in "sibils-like" fetch v3 raw format
    obj_v3 = mongo_pam_fetcher.fetch_v3_data(pmc_list[0])
    print("pmcid", obj_v3.get("pmcid"))
    print("anotations", 0 if obj_v3.get("annotations") is None else len(obj_v3.get("annotations")) )
    print("sentences", 0 if obj_v3.get("sentences") is None else len(obj_v3.get("sentences")) )
    print("document", 0 if obj_v3.get("document") is None else len(obj_v3.get("document")) )

    # get an object in "sibils-like" fetch_PAM format
    obj_v3 = mongo_pam_fetcher.fetch_v3_data(pmc_list[0])
    formatter = PmcaFormatter()
    formatter.build_v2_style(obj_v3)
    print("pmcid", obj_v3.get("pmcid"))
    print("anotations", 0 if obj_v3.get("annotations") is None else len(obj_v3.get("annotations")) )
    print("sentences", 0 if obj_v3.get("sentences") is None else len(obj_v3.get("sentences")) )


    print("End")
