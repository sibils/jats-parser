

#---------------------------
class TextFormatter:
#---------------------------

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
    def __init__(self, publi_obj):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
        self.publi_obj = publi_obj


    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
    def get_text_format(self, show_cnt_tag=False, show_cnt_id=False):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

        lines = list()

        doc = self.publi_obj["document"]

        # ...................
        # identifiers
        # ...................
        items = list()
        items.append(doc.get("medline_ta"))
        items.append(doc.get("publication_date"))
        items.append(doc.get("volume"))
        issue = doc.get("issue")
        if issue: items.append("(" + issue + ")")
        items.append(doc.get("medline_pgn"))
        pmcid = doc.get("pmcid")
        if pmcid: items.append("- PMCID: " + pmcid)
        pmid = doc.get("pmid")
        if pmid: items.append("- PMID: " + pmid)
        doi = doc.get("doi")
        if doi: items.append("- DOI: " + doi)
        treat_id = doc.get("treatment_bank_uri")
        if treat_id: items.append("Plazi treatment ID: " + treat_id)
        zen_id = doc.get("zenodo_doi")
        if zen_id: items.append("Zenodo DOI: " + zen_id)
        cleaned_items = list(filter(str.strip, items))
        lines.append(" ".join(cleaned_items))

        # build dictionary for affiliations id => label
        affid2label = dict()
        for aff in doc.get("affiliations") or []:
            id = aff.get("id")
            label = aff.get("label")
            if id and label:
                affid2label[id]=label
            elif id and not label: 
                affid2label[id]=id
            elif not id and label: 
                affid2label[label]=label

        # ...................
        # authors
        # ...................
        items = list()
        for auth in doc.get("authors") or []:
            aff_list = list()
            for aff in auth.get("affiliations") or []:
                label = affid2label.get(aff)
                if label: 
                    aff_list.append(label)
                else:
                    aff_list.append(aff)
            aff_str = ",".join(aff_list)            
            name = auth.get("name")
            if aff_str: name = f"{name} ({aff_str})"
            items.append(name)
        cleaned_items = list(filter(str.strip, items))
        if len(lines[-1])>0: lines.append("")
        lines.append("Author(s)")
        lines.append(", ".join(cleaned_items))

        # ...................
        # affiliations
        # ...................
        items = list()
        for aff in doc.get("affiliations") or []:
            label = aff.get("label")
            name = aff.get("name")
            if label: name = f"({label}) {name}"
            items.append(name)
        cleaned_items = list(filter(str.strip, items))
        if len(cleaned_items)>0:
            if len(lines[-1])>0: lines.append("")
            lines.append("Affiliations(s)")
            for item in cleaned_items: lines.append(item)

        # ...................
        # keywords
        # ...................
        items = list()
        for k in doc.get("keywords") or []:
            items.append(k)
        cleaned_items = list(filter(str.strip, items))
        if len(cleaned_items)>0:
            if len(lines[-1])>0: lines.append("")
            lines.append("Keywords(s)")
            lines.append(", ".join(cleaned_items))

        # ...................
        # sections
        # ...................
        for section_type in ["body_sections", "float_sections", "back_sections"]:
            for sct in doc[section_type]:
                sct_title = sct["title"]
                sct_id = sct["id"]
                if sct_id == "1": sct_title = "[Title]"
                if sct_id == "2": sct_title = "Abstract"
                if sct_id == "3": sct_title = "[Body sections]"
                if sct_id == "4": sct_title = "[Float sections]"
                if sct_id == "5": sct_title = "[Back sections]"
                # special cases for content with tag = 'notes' which are wrapped in a pseudo section
                print("sct id:", sct_id)
                if sct.get("tag") == "wrap":
                    if len(sct["contents"])>0:
                        if sct["contents"][0].get("tag") == "notes": sct_title = "Notes"
                # we remove first digit and first dot
                sct_id = sct_id[2:] 
                if len(lines[-1])>0: lines.append("")                
                lines.append(f"{sct_id} {sct_title}".strip())
                lines.append("")                
                for cnt in sct["contents"]:
                    print("real cnt_id:", cnt["id"])
                    cnt_tag = cnt["tag"]
                    cnt_id = cnt["id"][2:]
                    elems = list()
                    if show_cnt_id: elems.append(cnt_id)
                    if show_cnt_tag: elems.append(f"[{cnt_tag}]")
                    if cnt_tag == "fig":
                        lbl = cnt["label"]
                        rid = cnt.get("xref_id")
                        if rid: lbl = f"{lbl} ({rid})"
                        if len(lines[-1])>0: lines.append("")
                        elems.append(lbl)
                        lines.append(" ".join(elems))
                        url = cnt.get("xref_url")
                        if url: lines.append(url)
                        cpt = cnt.get("caption")
                        if cpt: lines.append(cpt)
                    else:
                        elems.append(cnt["text"])
                        lines.append(" ".join(elems))

        return "\n".join(lines)