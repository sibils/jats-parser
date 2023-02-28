import json

pmc_list = ["PMC2828183","PMC3082999","PMC3211372","PMC3284193"]

for pmc in pmc_list:
    with open("split/bib_" + pmc + ".json") as f:
        bib_data = json.load(f)
    with open("split/ana_" + pmc + ".json") as f:
        ana_data = json.load(f)
    with open("split/sen_" + pmc + ".json") as f:
        sen_data = json.load(f)

    bib_data["annotations"] = ana_data["annotations"]
    bib_data["sentences"] = sen_data["sentences"]

    outfile = "merged/" + bib_data["_id"] + ".json"
    with open(outfile, "w") as fo:
        json.dump(bib_data, fo)

