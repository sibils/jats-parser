# run with: python3 -m pytest test_get_affiliations.py
from lxml import etree
from process_xml import convert_leading_sup_to_label_in_affs, get_affiliations


def parse_aff(aff_xml):
    root = etree.fromstring(f"<article><front><article-meta>{aff_xml}</article-meta></front></article>")
    # same order as the preprocessing in parse_PMC_XML_core
    convert_leading_sup_to_label_in_affs(root)
    etree.strip_tags(root, "sup")
    etree.strip_tags(root, "italic")
    return get_affiliations(root)[0]


def test_wrap_with_ror_and_address_tags():
    aff = parse_aff("""<aff id="aff1">
<label>1</label>
<institution-wrap>
<institution-id institution-id-type="ror">https://ror.org/02rkvz144</institution-id>
<institution>Jilin Provincial Key Laboratory of Animal Resource and Ecological Security, Northeast Normal University</institution>
</institution-wrap>
<addr-line>Changchun</addr-line>
<country>China</country>
</aff>""")
    assert aff == {
        "id": "aff1",
        "ror_id": "https://ror.org/02rkvz144",
        "label": "1",
        "name": "Jilin Provincial Key Laboratory of Animal Resource and Ecological Security, Northeast Normal University Changchun China",
    }


def test_plain_text_with_formatting():
    aff = parse_aff("""<aff id="aff1">
<label>1</label>
<italic toggle="yes">Department of Oral and Maxillofacial Pathology, Government Dental College, Kottayam, Kerala, India. </italic>
</aff>""")
    assert aff == {
        "id": "aff1",
        "ror_id": "",
        "label": "1",
        "name": "Department of Oral and Maxillofacial Pathology, Government Dental College, Kottayam, Kerala, India.",
    }


def test_several_identifiers_and_institutions_with_text_after_wrap():
    aff = parse_aff("""<aff id="Aff1"><label>1</label><institution-wrap>
<institution-id institution-id-type="ROR">https://ror.org/034t30j35</institution-id>
<institution-id institution-id-type="GRID">grid.9227.e</institution-id>
<institution-id institution-id-type="ISNI">0000 0001 1957 3309</institution-id>
<institution>Institute of Chemistry, </institution>
<institution>Chinese Academy of Sciences, </institution>
</institution-wrap>Beijing, 100190 China </aff>""")
    assert aff["ror_id"] == "https://ror.org/034t30j35"
    assert aff["name"] == "Institute of Chemistry, Chinese Academy of Sciences, Beijing, 100190 China"


def test_identifier_other_than_ror_is_not_kept():
    aff = parse_aff("""<aff id="a"><label>3</label><institution-wrap>
<institution-id institution-id-type="Ringgold">29352</institution-id>
<institution>Government Medical College</institution></institution-wrap>, Pathanamthitta, India</aff>""")
    assert aff["ror_id"] == ""
    assert aff["name"] == "Government Medical College, Pathanamthitta, India"


def test_all_text_is_kept_when_institution_and_country_are_direct_children():
    aff = parse_aff("""<aff id="aff3"><label>3</label>
<institution content-type="department">Clinical Research</institution>,
<institution>National Institute for Medical Research</institution>,
<addr-line content-type="city">Dar es Salaam</addr-line>,
<country>Tanzania</country></aff>""")
    assert aff["name"] == "Clinical Research, National Institute for Medical Research, Dar es Salaam, Tanzania"


def test_leading_sup_becomes_the_label():
    aff = parse_aff("""<aff id="aff1">
<sup>1</sup>
<institution>Children's Hospital</institution>, <addr-line>Toulouse</addr-line>, <country>France</country>
</aff>""")
    assert aff["label"] == "1"
    assert aff["name"] == "Children's Hospital, Toulouse, France"


def test_sup_in_label_and_label_tail():
    aff = parse_aff("""<aff id="aff1"><label><sup>1</sup></label>Virginia College, Blacksburg, USA</aff>""")
    assert aff["label"] == "1"
    assert aff["name"] == "Virginia College, Blacksburg, USA"


def test_sup_after_text_is_not_a_label():
    aff = parse_aff("""<aff id="a">School of Life<sup>2</sup> Sciences</aff>""")
    assert aff["label"] == ""


def test_only_original_institution_is_used_when_available():
    aff = parse_aff("""<aff id="aff1"><label>1</label>
<institution content-type="original">. Universidad de Santander, Facultad de Ciencias, Colombia.</institution>
<institution content-type="normalized">Universidad de Santander</institution>
<institution content-type="orgname">Universidad de Santander</institution>
<country country="CO">Colombia</country></aff>""")
    assert aff["name"] == "Universidad de Santander, Facultad de Ciencias, Colombia."


def test_email_is_kept_and_missing_id_is_none():
    aff = parse_aff("""<aff><institution>Hanoi University</institution>
<country>Vietnam</country><email>someone@example.org</email></aff>""")
    assert aff["id"] is None
    assert aff["label"] == ""
    assert aff["name"] == "Hanoi University Vietnam someone@example.org"
