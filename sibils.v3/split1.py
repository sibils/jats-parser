max_ana= 4
with open("ftp_mirror/ana_pmc21n0002") as f:
    doc_num = 0
    current_id= ""
    record = ""
    while True:
        line = f.readline()
        if line == "": break
        if doc_num > max_ana: break
        str = line.strip()
        if str[:5] == "\"_id\"":
            if current_id != "":
                with open("split/ana_" + current_id + ".json", "w") as fo:
                    fo.write("{ \"_id\": \"" + current_id + "\",\n")
                    record = record[: record.rfind(",")]
                    fo.write(record)
                record = ""
            current_id = str[6:].strip().replace("\"","").replace(",","")
            doc_num +=1
            print(line, current_id)
        elif current_id != "" and str[:4] == "\"PMC":
            pass
        elif current_id != ""  :
            record += line


max_bib= 4
with open("ftp_mirror/bib_pmc21n0002") as f:
    doc_num = 0
    current_id= ""
    record = ""
    while True:
        line = f.readline()
        if line == "": break
        if doc_num > max_bib: break
        str = line.strip()
        if str[:5] == "\"_id\"":
            if current_id != "":
                with open("split/bib_" + current_id + ".json", "w") as fo:
                    fo.write("{ \"_id\": \"" + current_id + "\",\n")                    
                    record = record[: record.rfind("{")]
                    record = record[: record.rfind(",")]
                    fo.write(record)
                record = ""
            current_id = str[6:].strip().replace("\"","").replace(",","")
            doc_num +=1
            print(line, current_id)
        elif current_id != "":
            record += line


max_sen= 8
with open("ftp_mirror/sen_pmc21n0002") as f:
    doc_num = 0
    current_id= ""
    record = ""
    while True:
        line = f.readline()
        if line == "": break
        if doc_num > max_sen: break
        str = line.strip()
        if str[:5] == "\"_id\"":
            if current_id != "":
                with open("split/sen_" + current_id + ".json", "w") as fo:
                    fo.write("{ \"_id\": \"" + current_id + "\",\n")                    
                    record = record[: record.rfind("{")]
                    record = record[: record.rfind(",")]
                    fo.write(record)
                record = ""
            current_id = str[6:].strip().replace("\"","").replace(",","")
            doc_num +=1
            print(line, current_id)
        elif current_id != "":
            record += line


