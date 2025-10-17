import sys
import re
from lxml import etree
from pathlib import Path

def get_file_content(name):
	f = open(name,'r')
	f_text = f.read()
	f.close()
	return f_text

def cleanup_input_xml(xmlstr):

	# we remove everything before first appearance of <article...>
	pos = xmlstr.index("<article")
	xmlstr = xmlstr[pos:]

	# we remove everything after last appearance of </article>
	pos = xmlstr.rindex("</article>") + 10
	xmlstr = xmlstr[0:pos]

	# we remove any default namespace in document
	xmlstr = re.sub('xmlns="\S*?"', '', xmlstr)

	# we add an extra space after end of comment tag '-->'
	xmlstr = xmlstr.replace("-->","--> ")
	return xmlstr

def store_steps(steps, store):
    tags = list()
    for n in steps: tags.append(n.tag)
    steps_str = " / ".join(tags)
    if steps_str not in store: store[steps_str] = 0
    store[steps_str] += 1     


def visit(node, steps, store):
    steps.append(node)
    children = list()
    for n in node: children.append(n)
    if len(children)== 0:
        store_steps(steps, store)
    else:
        for n in node: visit(n, steps, store)
    steps.pop()

def get_path_to_root(node):
    tags = [ node.tag ]
    parent = node.getparent()
    while parent is not None:
        tags.append(parent.tag)
        parent = parent.getparent()
    return " / ".join(tags)

# 
# -----------------------------------------------------
# 

store = dict()
parent_dic = dict()
rlnum = 0
no_ref = 0
no_ttl = 0
no_ref_lbl = 0
no_p = 0
xml_files = Path('tmp').rglob('*.xml')
for filepath in xml_files:
    filename = filepath.resolve()
    print("parsing", filename, "...")
    xmlstr = get_file_content(filename)
    xmlstr = cleanup_input_xml(xmlstr)
    root = etree.fromstring(xmlstr)
    #elems = root.xpath("//ref-list")
    #elems = root.xpath("//ack")
    elems = root.xpath("//app")
    if len(elems)==0: continue
    for reflist in elems:
        rlnum += 1
        parent_path = get_path_to_root(reflist)
        if parent_path not in parent_dic: parent_dic[parent_path] = 0
        parent_dic[parent_path] += 1
        if len(reflist.xpath("ref")) == 0:
            no_ref += 1
            print("WARNING", filename, "No ref in ref-list")
        if len(reflist.xpath("ref/label")) == 0:
            no_ref_lbl += 1
            print("WARNING", filename, "No ref / label in ref-list")        
        if len(reflist.xpath("title")) == 0:
            no_ttl += 1
            print("WARNING", filename, "No title in ref-list")
        if len(reflist.xpath("p")) == 0:
            no_p += 1
            print("WARNING", filename, "No p in ref-list")
        else:
            #print("title:", reflist.find("title").text)
            pass
        visit(reflist,  list(), store)

print("\n------------- children of ref-list -------------\n")
for k in sorted(store.keys()):
    print(f"{store[k]:>5d} : {k}") 

print("\n------------- parents of ref-list --------------\n")
for k in sorted(parent_dic.keys()):
    print(f"{parent_dic[k]:>5d} : {k}") 
     

print("\n------------- specific stats of ref-list -------\n")
print("no_ref     :", no_ref, "/", rlnum)
print("no_ref_lbl :", no_ref_lbl, "/", rlnum)
print("no_ttl     :", no_ttl, "/", rlnum)
print("no_p     :", no_p, "/", rlnum)

print("\nend")
sys.exit()



