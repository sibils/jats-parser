# JAT parsing
The project contains python scripts parsing the Europe PMC interchange format JATS using the lxml library

See https://jats.nlm.nih.gov/archiving/tag-library/1.0/index.html?attr=article-type

See also https://lxml.de/parsing.html 

## How to use

### process_xml.py

Turns a PMC publication file (in XML JATS format) into json file written on the disk and send some stats on stdout

The *data* diectory contains some XML JATS publication files copied from  Europe PMC for test purpose

The json output is written in the *out* subirectory

**Usage**

Parsing a single file

    python ./process_xml.py ./data/3_Biotech/PMC3339582.xml
    less ./out/33/pmc3339582.json

Parsing a list of files

    find data -name "*.xml" -exec python ./process_xml.py {} \;

### jsonpmc_httpserver.py

Simple http server providing a json version of a publication given a pmcid.

The server listen http requests on port 8088 and responds ro requests like _/parse/pmc/{som pmcid}_ .

The server retrieves the XML JAT version of the corresponding publication by calling the ebi API.

It then uses **process_xml.py** to parse the XML. The response is a json version of the publication.

**Usage**

    python ./jsonpmc_httpserver.py > mylog 2>&1 &
    # wait 5 seconds
    curl http://localhost:8088/parse/pmc/3507161
    
## How to install the utility

### How to activate python3 environment:

https://wsvincent.com/install-python3-mac/

    # activate:
    source ~/.virtualenvs/myvenv/bin/activate
    
    # deactivate:
    deactivate

### How to install and use beautiful soup and lxml:

https://www.crummy.com/software/BeautifulSoup/bs4/doc/

    pip install beautifulsoup4e
    pip install lxml
