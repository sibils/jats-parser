# JATS parsing

This is a repository of the BiTeM group of the HES-SO of Geneva, see <http://bitem.hesge.ch/>

It contains two families of tools:

* **SIBiLS API proxy and PAM formatter** (`sibils.v3/`): a small http server that fetches publications
  from the SIBiLS API and converts them into the *PAM* format used by the publication viewer.
  It supports the collections pmc, medline, plazi, zenodo and suppdata.
* **JATS parser** (`process_xml.py`, `jsonpmc_httpserver.py`, ...): python scripts parsing the
  Europe PMC interchange format JATS with the lxml library, see https://jats.nlm.nih.gov/archiving/tag-library
  and https://lxml.de/parsing.html

Contents

* [SIBiLS API proxy (PAM format)](#sibils-api-proxy-pam-format)
  * [Start / stop / status: pam_proxy.sh](#start--stop--status-pam_proxysh)
  * [Requests](#requests)
  * [Request examples, one per collection](#request-examples-one-per-collection)
  * [How each collection is converted to PAM](#how-each-collection-is-converted-to-pam)
* [JATS parser tools](#jats-parser-tools)
  * [process_xml.py](#process_xmlpy)
  * [jsonpmc_httpserver.py](#jsonpmc_httpserverpy)
  * [Start / stop / status: jsonpmc_server.sh](#start--stop--status-jsonpmc_serversh)
  * [Routes: /getxml/pmc, /parse/pmc and /pseudo/api/fetch](#routes-getxmlpmc-parsepmc-and-pseudoapifetch)
  * [Developing process_xml.py and pmca_formatter.py](#developing-process_xmlpy-and-pmca_formatterpy)
* [Installation](#installation)
* [Notes about the JATS parser](#notes-about-the-jats-parser)
* [License](#license)

## SIBiLS API proxy (PAM format)

`sibils.v3/sibils_api_proxy_server.py` listens on port **8089** and forwards fetch requests to
the SIBiLS API (`https://biodiversitypmc.sibils.org/api/fetch`).
When `format=PAM` is requested, the PAM format is built locally by `PmcaFormatter`
(`sibils.v3/pmca_formatter.py`, not the older copy at the repository root):

* the v3 sentences are turned into `body_sections` / `back_sections` / `float_sections`
  made of sections and contents (paragraphs, list items, figures, tables),
* each annotation is located in its content with `content_id`, `concept_offset_in_section`
  and `concept_length`, so the viewer can highlight it.

Without `format=PAM` the SIBiLS response is returned as is.

### Start / stop / status: pam_proxy.sh

The script `pam_proxy.sh` at the repository root manages the proxy as a background process.

    ./pam_proxy.sh start     # start the proxy on port 8089 (does nothing if already running)
    ./pam_proxy.sh status    # running? responding on port 8089?
    ./pam_proxy.sh stop      # stop it (SIGTERM, then SIGKILL after 5 s)
    ./pam_proxy.sh restart
    ./pam_proxy.sh log       # follow the server log

* pid file: `tmp/pam_proxy.pid`, log file: `tmp/pam_proxy.log` (`tmp/` is git ignored)
* `status` exit code: 0 running and responding, 1 running but port not responding, 3 not running
* the python interpreter can be changed with the `PYTHON` variable, e.g. `PYTHON=~/venv/bin/python ./pam_proxy.sh start`
* `sibils_api_proxy_server.py` starts the server as soon as it is imported,
  so do not import it from another script.

### Requests

    GET http://localhost:8089/sibils/api/fetch?col={collection}&ids={id}[&format=PAM][&covoc]

| Parameter | Description |
|---|---|
| `col` | collection: `pmc`, `medline`, `plazi`, `zenodo` or `suppdata` |
| `ids` (or `id`) | identifier of **one** publication in the collection |
| `format=PAM` | build the PAM format locally (otherwise the raw SIBiLS v3 response is returned) |
| `covoc` | forwarded to SIBiLS (adds the covoc annotations) |

Responses:

* `200`: the SIBiLS response object, its `sibils_article_set[0]` is the publication
  (in PAM format when `format=PAM`)
* `404`: the publication was not found, e.g. `{"error": {"message": "missing ids:..."}, ...}`
* `400`: any other path than `/sibils/api/fetch`

### Request examples, one per collection

All examples below were checked with the proxy (counts are the number of annotations in the PAM output).

| Collection | Example id | Item | PAM sections | Annotations |
|---|---|---|---|---|
| pmc | `PMC4909023` | full text article | Title, Abstract, body sections, ... | 2812 |
| medline | `724278` | Medline citation | Title, Abstract, MeSH terms | 54 |
| plazi | `000040332F2853C295734E7BD4190F05` | taxonomic treatment | Title, Treatment | 137 |
| zenodo | `16704443_0` | Zenodo record with full text | Title, Full text, Keywords | 2655 |
| suppdata | `PMC10230156_CTM2-13-e1283-s002.docx` | supplementary file of a PMC article | Title, Content | 206 |

    curl 'http://localhost:8089/sibils/api/fetch?col=pmc&format=PAM&ids=PMC4909023'
    curl 'http://localhost:8089/sibils/api/fetch?col=medline&format=PAM&ids=724278'
    curl 'http://localhost:8089/sibils/api/fetch?col=plazi&format=PAM&ids=000040332F2853C295734E7BD4190F05'
    curl 'http://localhost:8089/sibils/api/fetch?col=zenodo&format=PAM&ids=16704443_0'
    curl 'http://localhost:8089/sibils/api/fetch?col=suppdata&format=PAM&ids=PMC10230156_CTM2-13-e1283-s002.docx'

Quick look at the result:

    curl -s 'http://localhost:8089/sibils/api/fetch?col=suppdata&format=PAM&ids=PMC10230156_CTM2-13-e1283-s002.docx' \
      | python3 -c "import json,sys; p=json.load(sys.stdin)['sibils_article_set'][0]; print(p['title']); print([s['title'] for s in p['body_sections']], len(p['annotations']))"

Ids can be found with the SIBiLS search API, e.g.
`https://biodiversitypmc.sibils.org/api/search?q=cell+line+lung+metastasis&col=suppdata&n=20`
(the ids are the `_id` values in `elastic_output.hits.hits`).

### How each collection is converted to PAM

| Collection | PmcaFormatter method | Notes |
|---|---|---|
| pmc | `get_adapted_format_for_pmc` | sections, figures and tables come from the v3 document; annotations on section titles are not kept |
| medline | `get_adapted_format_for_medline` | builds Title, Abstract (one paragraph per line of the abstract), Keywords, MeSH terms and chemicals sections |
| plazi | `get_adapted_format_for_plazi` | Title = treatment title, Treatment = treatment text; `treatment_bank_uri` and `zenodo_doi` are kept |
| zenodo | `get_adapted_format_for_zenodo` | Title, Abstract, Full text (one paragraph per sentence), Keywords; `license`, `article_type`, `publication_types`, `zenodo_doi`. Restricted records have no text: metadata is kept, annotations are dropped (e.g. `13477188_0`) |
| suppdata | `get_adapted_format_for_suppdata` | one record = one supplementary file (pdf, docx, xlsx, jpg with OCR text...) of a PMC article, id = `{pmcid}_{filename}`. Title = `{filename} - supplement of: {parent article title}` (not annotated), Content = one paragraph per sentence; `license` from `document.licence`, `article_type` from `document.type`, `pmcid` links to the parent article. Spreadsheets give very long paragraphs (CSV text), jpg text comes from OCR and is noisy |

## JATS parser tools

### process_xml.py

Turns a PMC publication file (in XML JATS format) into a json file written on the disk and sends some stats on stdout

The *data* directory contains some XML JATS publication files copied from Europe PMC for test purpose

The json output is written in the *out* subdirectory

**Usage**

Parsing a single file

    python ./process_xml.py ./data/3_Biotech/PMC3339582.xml
    less ./out/33/pmc3339582.json

Parsing a list of files

    find data -name "*.xml" -exec python ./process_xml.py {} \;

### jsonpmc_httpserver.py

Simple http server providing a json version of a publication given a pmcid.

The server listens to http requests on port 8088 and responds to requests like _/parse/pmc/{some pmcid}_ .

The server retrieves the XML JATS version of the corresponding publication from the PMC Cloud Service (open access articles only) and keeps it in the *tmp* directory, which it checks first for later requests.

It then uses **process_xml.py** to parse the XML. The response is a json version of the publication.

**Usage**

    ./jsonpmc_server.sh start
    curl http://localhost:8088/parse/pmc/3507161

### Start / stop / status: jsonpmc_server.sh

The script `jsonpmc_server.sh` at the repository root manages the server as a background process.

    ./jsonpmc_server.sh start     # start the server on port 8088 (does nothing if already running)
    ./jsonpmc_server.sh status    # running? responding on port 8088?
    ./jsonpmc_server.sh stop      # stop it (SIGTERM, then SIGKILL after 5 s)
    ./jsonpmc_server.sh restart
    ./jsonpmc_server.sh log       # follow the server log

* pid file: `tmp/jsonpmc_server.pid`, log file: `tmp/jsonpmc_server.log` (`tmp/` is git ignored)
* `status` exit code: 0 running and responding, 1 running but port not responding, or port answered by
  a server not started with this script, 3 not running
* `start` refuses to run if port 8088 is already answered by a server not started with this script: stop that one first
* the python interpreter can be changed with the `PYTHON` variable, e.g. `PYTHON=~/venv/bin/python ./jsonpmc_server.sh start`

### Routes: /getxml/pmc, /parse/pmc and /pseudo/api/fetch

The three routes are successive views of the same publication. They all get the XML the same way,
so each one shows the result of one more processing step:

    tmp/ cache, or else PMC Cloud Service
      |
      +--> XML JATS ----------------------------------------> /getxml/pmc/{pmcid}
             |
             | process_xml.py (parse_PMC_XML)
             v
           parsed publication ------------------------------> /parse/pmc/{pmcid}
             |
             +--> wrapped in a SIBiLS-like response --------> /pseudo/api/fetch?ids={pmcid}
             |
             +--> pmca_formatter.py (PmcaFormatter) --------> /pseudo/api/fetch?ids={pmcid}&format=pam
             |
             +--> text_formatter.py (TextFormatter) --------> /pseudo/api/fetch?ids={pmcid}&format=txt

| Route | Response | Publication found in |
| ----- | -------- | -------------------- |
| `/getxml/pmc/{pmcid}` | the XML JATS file, unchanged | the response itself |
| `/parse/pmc/{pmcid}` | json: `success`, `query`, `data` | `data` |
| `/pseudo/api/fetch?ids={pmcid}` | json: same structure as a SIBiLS fetch response | `sibils_article_set[0].document` |
| `/pseudo/api/fetch?ids={pmcid}&format=pam` | json: same structure, publication in PAM format | `sibils_article_set[0]` |
| `/pseudo/api/fetch?ids={pmcid}&format=txt` | plain text | the response itself |

* The publication in `data` of `/parse/pmc` and in `document` of `/pseudo/api/fetch` is the same object.
* `{pmcid}` can be written with or without the `PMC` prefix. `/pseudo/api/fetch` accepts `ids=` or `id=`, with a single id.
* Errors are returned as http 400 with a json body, for instance for a publication which is not open access.
* `/pseudo/api/fetch` always returns the collection `pmc`, its `col` and `covoc` parameters have no effect.
  Calling it without any parameter makes the request fail without a json error.

Example:

    curl http://localhost:8088/getxml/pmc/13498323
    curl http://localhost:8088/parse/pmc/13498323
    curl 'http://localhost:8088/pseudo/api/fetch?ids=PMC13498323&format=pam'

### Developing process_xml.py and pmca_formatter.py

The server loads the python modules when it starts, so **restart it after each code change**.
A publication is only downloaded once, so restarts and repeated requests are fast.

**process_xml.py**: compare the input from `/getxml/pmc` with the output from `/parse/pmc`.
The json keys are sorted, so the output before and after a change can be compared with `diff`:

    curl -s http://localhost:8088/parse/pmc/13498323 > tmp/before.json
    # ... edit process_xml.py ...
    ./jsonpmc_server.sh restart
    curl -s http://localhost:8088/parse/pmc/13498323 > tmp/after.json
    diff tmp/before.json tmp/after.json

**pmca_formatter.py**: compare the input from `/pseudo/api/fetch?ids={pmcid}` with the output
from `/pseudo/api/fetch?ids={pmcid}&format=pam`, in the same way. A change in `process_xml.py` also shows
in the PAM output, since it is built from the parsed publication.

This route only tests a part of the formatter. Its `sentences` and `annotations` are always empty, so the
PAM output never has annotations. It also only covers the collection pmc. To test annotations or the other
collections, use the [SIBiLS API proxy](#sibils-api-proxy-pam-format), which runs the same `PmcaFormatter`
on real SIBiLS data:

    curl 'http://localhost:8089/sibils/api/fetch?col=pmc&format=PAM&ids=PMC4909023'

**Tips**

* If a parsing or formatting error occurs, the client gets an empty response and the python traceback is in the log: `./jsonpmc_server.sh log`
* To try a specific XML case, edit the cached file (e.g. `tmp/PMC13/PMC13498323/PMC13498323.1.xml`), no restart needed.
  Delete the publication directory (e.g. `tmp/PMC13/PMC13498323/`) to download the file again on the next request.
* `pmca_formatter.py` is in `sibils.v3/`. `jsonpmc_server.sh` adds this directory to `PYTHONPATH` so the server can import it.

## Installation

The SIBiLS API proxy only needs python 3 (standard library) and curl for `pam_proxy.sh status`.

The JATS parser needs beautiful soup and lxml.

### How to activate python3 environment:

https://wsvincent.com/install-python3-mac/

    # activate:
    source ~/.virtualenvs/myvenv/bin/activate

    # deactivate:
    deactivate

### How to install and use beautiful soup and lxml:

https://www.crummy.com/software/BeautifulSoup/bs4/doc/

    pip install beautifulsoup4
    pip install lxml

## Notes about the JATS parser

### Main object structure

The parsing of the publication produces a json object. It is a dictionary with the following fields:

* _id : the numeric part of the PMC identifier
* pmcid, pmid, doi : publication identifiers when available
* journal, issue, volume, start_page, end_page, medline_pgn, medline_ta : journal infos
* affiliations : an array of elements with the fields id, ror_id (empty string if none), label and name (the full text of the affiliation, without the label and the institution identifiers)
* authors
* publication_date, publication_date_alt, publication_year
* article_type
* keywords : an array of keywords
* full_title
* abstract
* body_sections : an array of elements with the publication content, the publication title and the abstract are the first two sections in the array (if they exist)
* back_sections : sections related to the back content of the document (appendices, supplementary material, ...)
* float_sections : sections which are included in the publication but not in flow ot the body text (i.e. boxed-text)

### Section structure

The objects to be found in the body, back and float sections can be aither sections, appendices, or boxed-text.

**id**

A string identifying the section generated during the parsing process.
Sections found in the XML can embed each other. But in the generated json they are all siblings, flattened in a sequence (in the _body_section_ array for example).
The hierarchical structure of the section and of any of its content is reflected in its id.
For instance, a section with id _1.3.2_ comes just after section with id _1.3.1_ and both are subparts of section with id _1.3_ in the original XML.

**tag**

Usually the value is _sec_ but since we also handle appendices _app_ and boxed text _boxed-text_ the same way, the value of this tag may vary.

**level**

Reflects the embedding level of the section in the original XML file.
Sections that are children of the _body_ element in the XML have level 1.
A section that is a child of another _section_ that is a child of the _body_ element of the XML will have level 2.

**implicit**

The XML of many publications do not use sections of use paragraphs ( _p_ element ) outside of any section just below the _body_ element.
In this case, we create an _implicit_ section (equivalent to the body) to keep the json structure consistent.
The _title_ and _abstract_ sections are set as implicit.

**label**

The label of a section as given in the original XML. For instance, a section number.
Often empty.

**title**

The title of a section as given in the original XML.
Often empty.

**contents**

A list of textual elements that are part of the section.
Like sections, the content elements also have an _id_ reflecting their hierachical position in the XML tree.
The _tag_ is the name of the XML element containing the textual element.
The most common tags are paragraphs _p_ , list _list_item_ , figures _fig_ and tables _table_ .
The field _caption_ contains the text for _fig_ _boxed_text_ and _table_ elements.
The field _text_ contains the text for paragraphs _p_ and other elements.

Other tags (not _p_ nor _fig_ nor _table_ nor _list-item_) may appear but no particular effort was made to handle their textual content specifically.

### Handling figures

Figures (elements with tag = _fig_) have specific fields:

* label : the figure label as given in the XML
* caption : the figure caption as given in the XML
* graphics, media and pmcid : identifiers allowing to build an URL containing an image of the figure

In XML, _fig_ may appear in:

* _body_, _sec_ : the most usual cases
* _p_ : in this case, the paragraph is split in several subparts, the figure becoming one of them
* _fig-group_ : is removed from the XML, its tables are handled normally, see Endosc_Int_Open/PMC4423251.xml , Curr_Health_Sci_J/PMC3945237.xml
* _boxed-text_ : IGNORED. Are out of main body text flow: ignored by removing them
* _disp-quote_ : uses the default handler if not included in p or sec

### Handling tables

Tables (elements with tag = _table_) have specific fields:

* label : the table label as given in the XML
* caption : the table caption as given in the XML
* tableColumns : the name of the table column as  text
* tableValues : the values of the table cells as text
* graphics, media and pmcid : identifiers allowing to build an URL containing an image of the table
* xml : the XML to be used to display the table in an HTML page

In XML, _table-wrap_ may appear in:

* _sec_ : section is the most usual container of a table
* _body_ : in this case, the body is treated as a section
* _boxed-text_ :  is removed from the XML, its tables are handled normally
* _p_ : in this case, the paragraph is split in several subparts, the table becoming one of them. i.e. 3_Biotech/PMC3324826.xml
* _supplementary-material_ : is removed from the XML, its tables are handled normally, implicit _fig_ elements in it are also handled, see Biomark_Cancer/PMC3122269.nxml , Eur_J_Rheumatol/PMC6267743.nxml , Adv_Appl_Bioinform_Chem/PMC3459542.nxml
* _table-wrap-group_ : is removed from the XML, its tables are handled normally. Common label and caption tags are dispatched in each table in there. See Front_Genet/PMC3202977.nxml , Hum_Gene_Ther/PMC4442602.nxml ,	Intern_Med/PMC5088533.nxml , J_Hum_Reprod_Sci/PMC2700667.nxml
* _disp-quote_ : An extract or extended quoted passage from another work, usually made typographically distinct from surrounding text. The table caption appears as the _text_ value of the content element with tag _disp-quote_(default handler). See
J_Entrep_Educ/PMC5985942.nxml , Qual_Saf_Health_Care/PMC2602740.nxml
* _fig_ : IGNORED. A rare case. The table content only appears in the detailed figure popup but not in full text viewer on PMC website, so the table-wrap content ignored in this case. See Pharmaceutics/PMC2997712.nxml

### Encoding

alpha - α is seen as "\u03b1" in shell but as α in browser.
The _unidecode_ method used pubmed_oa_parser.py could also be used to turn greek letters and other special ones into their ascii closest equivalent.

### Info and changes published on 2019, Oct 8th

**pub_date elements**

_pub-date_ elements are searched in this order: date-type = pmc-release, then epub, ppub, collection, and finally any kind.
We return a full date (month is 1, day is 1 if missing)
If we had to set a default day or month, _publication_date_status_ = 'incomplete'
Example:
		publication_date: "05-4-2011",
		publication_date_alt: "2011 Apr 05",
		publication_date_status: "ok",
		pubyear: "2011",

**box-text elements**
Missing paragraph in boxed-text
Check PMC3887505
Now boxed text are handled like sections and inserted in the text flow

**table-wrap-foot elements**
table wrap footer can be multiple, we now handle that too
Check 5810844

**figures embedded in a list element**
Figures embedded in a list (itself in a paragraph in a section) are not parsed.
Check 5797209, 5729785
NOT FIXED

## License

This project is licensed under the terms of the GNU General Public License, version 3 or any later version (see file license.txt)
