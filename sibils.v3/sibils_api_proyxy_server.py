import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import http.client
from pmca_formatter import PmcaFormatter


class GP(BaseHTTPRequestHandler):

    def _set_headers(self,statusCode, content_type):
        self.send_response(statusCode)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

    def do_HEAD(self):
        self._set_headers(200)

    def buildErrorResponseObject(self, query, msg):
        response={}
        response['query']=query
        response['success']=False
        error={}
        error['message']=msg
        response['error']=error
        return response

    def buildSuccessResponseObject(self, query, data):
        response={}
        response['query']=query
        response['success']=True
        response['data']=data
        return response

    def sendJsonResponse(self, obj, statusCode):
        str = json.dumps(obj, sort_keys=True, indent=2)
        self._set_headers(statusCode, 'application/json')
        self.wfile.write(bytes(str,'utf-8'))


    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
    def getSibilsPubli(self, id, col, formatPam=False, withCovoc=False):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
        # EXAMPLES
        # https://sibils.text-analytics.ch/api/v3.3/fetch?ids=PMC4909023&col=pmc
        # https://sibils.text-analytics.ch/api/v3.3/fetch?ids=724278&col=medline

        connection = http.client.HTTPSConnection("sibils.text-analytics.ch")
        url = "/api/v3.3/fetch"
        url += "?col=" + col
        if formatPam: url += "&format=PAM"
        if withCovoc: url += "&covoc"
        url += "&ids=" + id
        print("Call to sibils.text-analytics.ch:", url)
        
        connection.request("GET", url)
        response = connection.getresponse()
        data = response.read().decode("utf-8")
        obj = json.loads(data)
        connection.close()
        return obj


    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
    def do_GET(self):
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

        error_msg='ERROR, invalid URL: ' + self.path

        if self.path[0:20]=='/sibils/api/v3/fetch':
            formatPam = False
            withCovoc = False
            id="none"
            col="none"
            for param in self.path[20:].split('?')[1].split("&"):
                nv = param.split("=")
                if nv[0] == "id":  id = nv[1]
                if nv[0] == "ids":  id = nv[1]
                if nv[0] == "col": col = nv[1]
                if param == "format=PAM" : formatPam = True
                if param == "covoc" : withCovoc = True

            obj = self.getSibilsPubli(id, col, False, withCovoc)

            # we build the PAM format locally
            if formatPam==True:
                publi = obj["sibils_article_set"][0]
                collection = obj["collection"]
                formatter = PmcaFormatter()
                publi_pam = formatter.get_pmca_format(publi, collection)
                obj["sibils_article_set"][0] = publi_pam
                        
            self.sendJsonResponse(obj, 200)
            return

        print(error_msg)
        obj = self.buildErrorResponseObject(self.path, error_msg)
        self.sendJsonResponse(obj,400)


def run(server_class=HTTPServer, handler_class=GP, port=8089):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print('Server running at localhost:' + str(port) + '...')
    httpd.serve_forever()

# - - - - - - - - - - - - - - - - - - - - - - - - - -
# Main
# - - - - - - - - - - - - - - - - - - - - - - - - - -
run()
