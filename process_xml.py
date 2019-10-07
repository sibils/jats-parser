# Pam April 2019
# Parsing jats DTD, the standard for Europe PMC
# see https://jats.nlm.nih.gov/

import sys
import codecs
import os
import glob
import json
from optparse import OptionParser
from datetime import datetime
from lxml import etree
from unidecode import unidecode



def get_file_content(name):
	f = open(name,'r')
	# we remove this header which is redundant and puzzles the lxml parser
	if f.readline()== '<?xml version="1.0" encoding="UTF-8"?>\n':
		print('got header about UTF-8 encoding, will skip it')
	else:
		f.seek(0)
	f_text=f.read()
	f.close()
	return f_text

# helper function, used for stats printing
def get_cardinality(n):
	if n>1: return 'N'
	return str(n)

# helper function, used for stats printing
def get_el_cardinality(someroot, somepath):
	c = get_cardinality(len(someroot.xpath(somepath)))
	return somepath + ':' + c

# helper function, used for stats printing
def get_stats(fname, someroot):
	line = 'pam-stats' + '\t'
	line += fname + '\t'
	line += get_el_cardinality(someroot,'/article/front/article-meta/abstract') + '\t'
	line += get_el_cardinality(someroot,'/article/body/p') + '\t'
	line += get_el_cardinality(someroot,'/article/body/sec')
	return line

# helper function, used for stats printing
# lists the tags of elements containing a <fig> for a given file
def get_fig_parents(fname, someroot):
	parents={}
	figs = someroot.xpath('/article/body//fig')
	if figs is not None:
		for fig in figs:
			parent_tag=fig.getparent().tag
			if parents.get(parent_tag) is None: parents[parent_tag]=0
			parents[parent_tag]=parents[parent_tag]+1
	lines=[]
	for p in parents:
		line = 'fig-stats' + '\t' + fname + '\t<' + p + '>:' + str(parents[p])
		lines.append(line)
	return lines

# helper function, used for stats printing
# lists the tags of elements containing a <table-wrap> for a given file
def get_tw_parents(fname, someroot):
	parents={}
	tws = someroot.xpath('/article/body//table-wrap')
	if tws is not None:
		for tw in tws:
			parent_tag=tw.getparent().tag
			if parents.get(parent_tag) is None: parents[parent_tag]=0
			parents[parent_tag]=parents[parent_tag]+1
	lines=[]
	for p in parents:
		line = 'tw-stats' + '\t' + fname + '\t<' + p + '>:' + str(parents[p])
		lines.append(line)
	return lines


# helper function, used for stats printing
# lists the tags of elements that are direct children of <body>
def get_body_structure(fname, someroot):
	line = 'pam-struc' + '\t'
	line += fname + '\t'
	atype = someroot.xpath('/article')[0].get('article-type')
	line += atype + '\t'
	myroots = someroot.xpath('/article/body')
	if len(myroots)>0:
		myroot=myroots[0]
		for el in myroot.iterchildren():
			if isinstance(el, etree._Comment): continue
			line += el.tag + ','
	return line

def get_keywords(someroot):
	kwd_list = someroot.xpath('/article//kwd')
	if kwd_list is None: return []
	result = []
	for k in kwd_list:
		result.append(clean_string(' '.join(k.itertext())))
	return result

def get_multiple_texts_from_xpath(someroot, somepath, withErrorOnNoValue):
	result = ''
	x = someroot.xpath(somepath)
	for el in x: result += ' '.join(el.itertext())
	if len(result) >= 1:
		result=clean_string(result)
	elif withErrorOnNoValue:
		file_status_add_error("ERROR, no text for element: " + somepath)
	return result

def get_text_from_xpath(someroot, somepath, withWarningOnMultipleValues, withErrorOnNoValue):
	result = ''
	x = someroot.xpath(somepath)
	if len(x) >= 1:
		result = get_clean_text(x[0])
		#result = x[0].text
		if len(x) > 1 and withWarningOnMultipleValues is True :
			file_status_add_error('WARNING: multiple elements found: ' + somepath)
	elif withErrorOnNoValue is True:
		file_status_add_error("ERROR, no text for element: " + somepath)
	return result


def get_pub_date_by_type(someroot,selector,pubtype,format):

	if not pubtype is None: selector += '[@pub-type="' + pubtype + '"]'
	dates = someroot.xpath(selector);
	if len(dates)==0: return {'date': None, 'status':'not found'}
	dt = dates[0]

	status = 'ok'
	ynode = dt.find('year')
	year = ynode.text if ynode is not None and ynode.text is not None else ''
	if len(year)==0: return {'date': None, 'status': 'incomplete'}
	mnode = dt.find('month')
	mm = '01'
	if mnode is not None and mnode.text is not None:
		mm = mnode.text
	else:
		status = 'incomplete'
	mmm_names=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
	mmm = ''
	if mm.isdigit() and int(mm)>0 and int(mm)<=12:
		mmm = mmm_names[int(mm)-1]
	else:
		status = 'unparseable'
	dnode = dt.find('day')
	day = '01'
	if dnode is not None and dnode.text is not None:
		day = dnode.text
	else:
		status = 'incomplete'

	formatted_date = year + ' ' + mmm + ' ' + day # default format
	if format=='yyyy': formatted_date = year
	if format=='d-M-yyyy': formatted_date = day + '-' + mm + '-' + year
	return {'date': formatted_date, 'status': status}


# easiest way to retrieve publication date: take first in the list
def get_first_pub_date(someroot,format):
	selector = '/article/front/article-meta/pub-date'
	return get_pub_date_by_type(someroot, selector, None, format)

# alternative way to retrieve publication date: use precedence by pub-type
# precedence order: pmc-release, epub, ppub.
# we assume pmc-release and epub are complete dates (with month and day)
# we then try ppub and add month = 1 and day = 1 it they are tmissing
# algo decided in accordance with Julien
def get_pub_date(someroot,format):
	selector = '/article/front/article-meta/pub-date'
	dt = get_pub_date_by_type(someroot, selector, 'pmc-release', format)
	if dt['status'] is not 'ok': dt = get_pub_date_by_type(someroot, selector, 'epub', format)
	if dt['status'] is not 'ok': dt = get_pub_date_by_type(someroot, selector, 'ppub', format)
	if dt['status'] is not 'ok': dt = get_pub_date_by_type(someroot, selector, 'collection', format)
	if dt['status'] is not 'ok': dt = get_pub_date_by_type(someroot, selector, None, format)
	if dt['status'] is not 'ok': file_status_add_error('ERROR, element not found: ' + selector)
	return dt

def build_medlinePgn(fp,lp):
	if fp!=None and len(fp)>0 and lp!=None and len(lp)>0: return fp + '-' + lp
	if fp!=None and len(fp)>0: return fp + '-?'
	if lp!=None and len(lp)>0: return '?-' + lp
	return ''


def get_affiliations(someroot):
	result=[]
	affs = someroot.xpath('/article/front/article-meta//aff')
	for aff in affs:
		id=aff.get('id')
		# extract label text and then remove node
		label_node = aff.find('label')
		label = get_clean_text(label_node)
		# !!! DO NOT USE line below: it removes the node tail as well
		# if label_node is not None: aff.remove(label_node, keep_tail=True)
		# use line below instead
		if label_node is not None: label_node.text = ''
		# try to build name from institut and country
		institution = get_clean_text(aff.find('institution'))
		country = get_clean_text(aff.find('country'))
		if len(institution)>0 and len(country)>0:
			name = institution + ', ' + country
		# otherwise build name from any text found in there
		else:
			name = get_clean_text(aff)

		result.append({'id':id, 'label':label, 'name': clean_string(name)})
	return result

def get_authors(someroot):
	authors = someroot.xpath('/article/front/article-meta/contrib-group/contrib[@contrib-type="author"]');
	result = []
	for a in authors:
		surname = ''
		givennames = ''
		affiliation_list = []
		for el in a.iter():
			if el.tag == 'surname':
				if el.text != None: surname = clean_string(el.text)
			elif el.tag == 'given-names':
				if el.text != None: givennames = clean_string(el.text)
			# affiliations
			elif el.tag == 'xref' and el.get('ref-type')=='aff':
				if el.get('rid') != None: affiliation_list.append(el.get('rid'))
			# affiliations (alternative)
			elif el.tag == 'aff':
				if el.text != None: affiliation_list.append(clean_string(el.text))

		author = {}
		author['affiliations'] = affiliation_list
		author['last_name'] = surname
		author['first_name'] = givennames
		author['name'] = (givennames + ' ' + surname).strip()
		author['initials'] = get_initials(givennames)
		result.append(author)
	if len(result)==0: file_status_add_error("WARNING: no authors")
	return result

def get_initials(multiple_names):
	if multiple_names=='': return ''
	names = multiple_names.split(' ')
	initials = ''
	for name in names:
		# sometimes we have consecutive spaces in names causing name = ' '
		if len(name.strip()) > 0: initials += name[0]
	return initials

def clean_string(s1):
	# replaces new line, unbreakable space, TAB with SPACE and strip the final string
	# also replaces multiple spaces with a single one
	if s1 is None: return None
	s2 = s1.replace('\n', ' ').replace(u'\u00a0', ' ').replace('\t', ' ').strip()
	return ' '.join(s2.split())


def get_abstract(someroot):
	x = someroot.xpath('/article/front/article-meta/abstract')
	content=''
	for xi in x:
		content += ' '.join(xi.itertext()) + ' '
	return clean_string(content)



# helper function, for stats printing
def indent(level):
	spaces = ''
	for i in range(1,level): spaces += '  '
	return spaces

def coalesce(*arg):
  for el in arg:
    if el is not None:
      return el
  return None

# we remove any boxed-text from the XML tree
# they are not in the body text flow (illustrative prurpose)
# this is a temp simple solution
# rare case: less than 1 < 10'000 publication
def handle_boxed_text_elements(someroot):
	bt_list = someroot.xpath('//boxed-text')
	if bt_list is None: return
	if bt_list==[]: return
	for bt in bt_list: bt.getparent().remove(bt)
	file_status_add_error('WARNING: removed some <boxed-text> element(s)')

# we remove all elements and their subtree having tag in tag_list
def remove_subtree_of_elements(someroot, tag_list):
	el_list = someroot.iter(tag_list)
	for el in el_list: el.getparent().remove(el)


def handle_table_wrap(pmcid, tw):
	xref_id = tw.get('id') or ''
	xref_url = 'https://www.ncbi.nlm.nih.gov/pmc/articles/' + pmcid + '/table/' + xref_id
	label=get_clean_text(tw.find('label'))
	caption=get_clean_text(tw.find('caption'))
	footer=get_clean_text(tw.xpath('table-wrap-foot'))
	media_hrefs = [ get_xlink_href(el) for el in tw.xpath('media') ]
	graph_hrefs = [ get_xlink_href(el) for el in tw.xpath('graphic') ]
	# table content
	columns=[]
	row_values=[]
	table_xml=b''
	table_tree = tw.find('table')
	if table_tree is None: table_tree = tw.find('alternatives/table')
	if table_tree is not None:
		table_xml = etree.tostring(table_tree)
		columns, row_values = table_to_df(table_xml)
	return {'tag': 'table', 'xref_id': xref_id, 'xref_url': xref_url,
			'label': label, 'caption': caption, 'footer':footer,
			'media':media_hrefs, 'graphics':graph_hrefs,
			'table_columns': columns, 'table_values': row_values,
			'xml':table_xml.decode("utf-8")}


def table_to_df(table_text):
	table_tree = etree.fromstring(table_text)
	columns = []
	for tr in table_tree.xpath('thead/tr'):
		for c in tr.getchildren():
			columns.append(' '.join(c.itertext()))

	row_values = []
	len_rows = []
	for tr in table_tree.findall('tbody/tr'):
		es = tr.xpath('td')
		row_value = [' '.join(e.itertext()) for e in es]
		len_rows.append(len(es))
		row_values.append(row_value)

	if len(len_rows) >= 1:
		len_row = max(set(len_rows), key=len_rows.count)
		row_values = [r for r in row_values if len(r) == len_row] # remove row with different length
		return columns, row_values
	else:
		return None, None

def get_clean_text(el):
	if el is None: return ''
	if type(el) == list:
		# sub_str_list = []
		# for sub_el in el: sub_str_list.append(' '.join(sub_el.itertext()))
		# return clean_string(' '.join(sub_str_list))
		return clean_string(' '.join([' '.join(sub_el.itertext()) for sub_el in el]))
	else:
		return clean_string(' '.join(el.itertext()))

def modify_insert_text_in_sub_element(ins_texts, subel_tag, el):
	texts=[]
	texts.extend(ins_texts)
	subel = el.find(subel_tag) # only first match cos cardinality for caption and label is 0-1
	if (subel is not None): texts.append(' '.join(subel.itertext()))
	new_text = clean_string(' '.join(texts))
	# rebuild subelement with its new text content
	for subel in el.iterchildren(subel_tag): el.remove(subel)
	new_subel = etree.SubElement(el, subel_tag)
	new_subel.text = new_text

# easy way to get value of
# attribute 'href' or '{http://www.w3.org/1999/xlink}href'
def get_xlink_href(el):
	if el is None: return None
	for k in el.keys():
		if k[-4:]=='href': return el.get(k)
	return None

# modifies the original XML by:
# 1. moving <table-wrap> elements next to their embedding <supplementary_material> element
# 2. removing <supplementary_material> elements from XML
# Note: we ignore implicit embedded figure (there may be a figure label, caption, etc...)
def handle_supplementary_material_elements(someroot):
	etree.strip_tags(someroot,'supplementary-material')

def handle_supplementary_material_elements_ori(someroot):
	sm_list = someroot.xpath('//supplementary-material')
	if sm_list is None: return
	for sm in sm_list:
		for el in sm.iterchildren('table-wrap','p','fig'):
			sm.addprevious(el)

		# # After moving <table-wrap> elements try build a figure obj with the remaining content if any
		# # Note: we create a figure but if might be a table as well we can't guess...
		# label=get_clean_text(sm.find('label'))
		# caption=get_clean_text(sm.find('caption'))
		# media=[ get_xlink_href(m) for m in sm.xpath('media') ]
		# graph=[ get_xlink_href(g) for g in sm.xpath('graphic') ]
		# if (label != '' or caption != '') and (len(media)>0 or len(graph)>0):
		# 	fig = etree.SubElement(sm.getparent(), 'fig')
		# 	fig.attrib['id']='' # there is a special handling of figure with no id
		# 	etree.SubElement(fig,'label').text=label
		# 	etree.SubElement(fig,'caption').text=caption
		# 	for m in media: etree.SubElement(fig,'media').attrib['href']=m
		# 	for g in graph: etree.SubElement(fig,'graphic').attrib['href']=g

		# removes supplementary_material which is now unnecesssary
		sm.getparent().remove(sm)


# modifies the original XML by:
# 1. adding <table-wrap-group> caption and label text to each child <table-wrap> element caption
# 2. moving <table-wrap> elements next to their embedding <table-wrap-group>
# 3. removing <table-wrap-group> elements from XML
def handle_table_wrap_group_elements(someroot):
	g_list = someroot.xpath('//table-wrap-group')
	if g_list is None: return
	for g in g_list:
		# store table-wrap-group caption and label
		g_captions=[]
		for gc in g.iterchildren('caption'): g_captions.append(' '.join(gc.itertext()))
		g_labels=[]
		for gl in g.iterchildren('label'): g_labels.append(' '.join(gl.itertext()))
		for tw in g.xpath('table-wrap'):
			modify_insert_text_in_sub_element(g_labels, 'label', tw)
			modify_insert_text_in_sub_element(g_captions, 'caption', tw)
			# moves tw as the previous sibling of table-wrap-group
			g.addprevious(tw)
		# removes fig-group which is now unnecesssary
		g.getparent().remove(g)


# modifies the original XML by
# 1. moving <el_tag> elements next to their embedding <el_tag>-group
# 2. removing <el_tag>-group from elements from XML
def remove_embedding_group_elements(someroot, el_tag):
	g_list = someroot.xpath('//' + el_tag + '-group')
	if g_list is None: return
	for g in g_list:
		for el in g.xpath(el_tag):
			g.addprevious(el)
		g.getparent().remove(g)

# modifies the original XML by
# 1. adding <fig-group> caption text to each child <fig> element caption
# 2. moving <fig> elements next to their embedding <fig-group>
# 3. removing <fig-group> from elements from XML
def handle_fig_group_elements(someroot):
	fg_list = someroot.xpath('//fig-group')
	if fg_list is None: return
	for fg in fg_list:
		# store fig-group caption
		fg_captions=[]
		for fgc in fg.iterchildren('caption'): fg_captions.append(' '.join(fgc.itertext()))
		for fig in fg.xpath('fig'):
			modify_insert_text_in_sub_element(fg_captions, 'caption', fig)
			# moves fig as the previous sibling of fig-group
			fg.addprevious(fig)
		# removes fig-group which is now unnecesssary
		fg.getparent().remove(fg)

def handle_fig(pmcid, fig):
	xref_id = fig.get('id') or ''
	xref_url = 'https://www.ncbi.nlm.nih.gov/pmc/articles/' + pmcid + '/figure/' + xref_id
	if xref_id == '': xref_url = ''
	fig_label = get_clean_text(fig.find('label'))
	fig_caption = get_clean_text(fig.find('caption'))
	media_hrefs = [ get_xlink_href(el) for el in fig.xpath('media') ]
	graph_hrefs = [ get_xlink_href(el) for el in fig.xpath('graphic') ]
	return {'tag':'fig', 'caption': fig_caption, 'xref_url': xref_url,
			'xref_id': xref_id, 'label': fig_label, 'media': media_hrefs,
			'graphics': graph_hrefs, 'pmcid':pmcid }


def handle_list(list):
	contentList=[]
	for el in list.iterchildren(['list-item']):
		contentList.append({'tag': 'list-item', 'text': clean_string(' '.join(el.itertext()))})
	tail = clean_string(list.tail)
	if tail is not None: contentList.append({'tag': 'p', 'text': tail})
	return contentList

# a paragraph <p> may contain <fig> and / or <table-wrap>  and / or <list> elements.
# if this is the case figs, tables and lists are parsed with their own handler
# and appended in order in the content list returned
def handle_paragraph(pmcid,el):
	simplify_node(el, ['fig','table-wrap','list'])
	contentList=[]
	ptext=clean_string(el.text)
	if ptext is not None and ptext != '': contentList.append({'tag':'p', 'text': ptext})
	#for sub_el in el.iterchildren(['fig','table-wrap','list']):
	# we should only have fig, table-wrap, list sub-elements after simplifying above
	for sub_el in el.iterchildren():
		if sub_el.tag == 'fig':
			# parse the inner fig and add result to content list
			contentList.append(handle_fig(pmcid,sub_el))
		elif sub_el.tag == 'table-wrap':
			# parse the inner table and add result to content list
			contentList.append(handle_table_wrap(pmcid,sub_el))
		elif sub_el.tag == 'list':
			contentList.extend(handle_list(sub_el))
		else:
			contentList.append({'tag':sub_el.tag, 'text': get_clean_text(sub_el)})
	ptail=clean_string(el.tail)
	if ptail is not None and ptail != '': contentList.append({'tag':'p', 'text': ptail})
	return contentList


def handle_paragraph_old(pmcid,el):
	contentList=[]
	for sub_el in el.iterchildren(['fig','table-wrap']):
		if sub_el.tag == 'fig':
			# parse the inner fig and add result to content list
			contentList.append(handle_fig(pmcid,sub_el))
		elif sub_el.tag == 'table-wrap':
			# parse the inner table and add result to content list
			contentList.append(handle_table_wrap(pmcid,sub_el))
		# remove fig / table from paragraph
		sub_el.getparent().remove(sub_el)
	# now we got rif of any table, fig, so let's build paragraph content and
	# set result at first rank in content list
	content = {'tag': el.tag, 'text': clean_string(' '.join(el.itertext()))}
	contentList.insert(0,content)
	return contentList


# recursive function used to parse the article body (or floats-group or back node too).
# the body tree is traversed depth first:
# on encountering a section <sec> or <app> or <boxed-text> element, the function calls itself
# on encountering <p>, <fig>, <list> and <table-wrap> elements, dedicated handlers are called
# on encountering another element, a default handler is used
def handle_section_flat(pmcid, sec, level, implicit, block_id):

	sectionList = []
	id = ''.join(sec.xpath('@id'))
	title = get_clean_text(sec.find('title'))
	caption = get_clean_text(sec.find('caption'))
	label = get_clean_text(sec.find('label'))
	mainSection = {'implicit':implicit, 'level': level, 'id': build_id(block_id),
		'title': title,
		'label': label,
		'caption': caption,
		'tag': sec.tag,
		'contents':[]}
	# we add main section to the list before any other sub sections
	sectionList.append(mainSection)
	# print(indent(level) + 'level: ' + str(level) + ' - name: ' + mainSection['name'])
	block_id.append(0)
	terminalContentShouldBeWrapped=False

	for el in sec:

		# ignore elements handled elsewhere or that are unnecessary
		if isinstance(el, etree._Comment): continue
		if el.tag == 'title': continue
		if el.tag == 'label': continue
		if el.tag == 'caption': continue

		# recursive call for any embedded section <sec>, <boxed-text> and/or <app> (appendices)
		if el.tag == 'sec' or el.tag == 'app' or el.tag == 'boxed-text':
			block_id[-1] = block_id[-1] + 1
			terminalContentShouldBeWrapped=True
			sectionList.extend(handle_section_flat(pmcid, el, level + 1, False, block_id))
			continue

		contentsToBeAdded=[]
		# handle paragraphs: will return paragraph content plus any embedded figures or tables as sibling contents
		if el.tag == 'p':
			contentsToBeAdded = handle_paragraph(pmcid, el)
		elif el.tag == 'fig':
			contentsToBeAdded = [ handle_fig(pmcid, el) ]
		elif el.tag == 'table-wrap':
			contentsToBeAdded = [ handle_table_wrap(pmcid, el) ]
		elif el.tag == 'list':
			contentsToBeAdded = handle_list(el)
		# default handler: just keep tag and get all text
		else:
			sometext = clean_string(' '.join(el.itertext()))
			if sometext is not None and sometext != '':
				contentsToBeAdded = [ {'tag': el.tag, 'text': sometext} ]

		addContentsOrWrappedContents(sectionList, mainSection, contentsToBeAdded, level, terminalContentShouldBeWrapped)

	block_id.pop()
	return sectionList

# We want the order of contents to be preserved during parsing
# When we meet a section having a mix of content types including a sub section the order may be lost if we don't wrap some contents
# XML Example:
# <sec id="main_sec">
#   <p id="p1">...</p>
#   <sec id="sub_sec"><p id="p2">...</p></sec>
#   <p id="p3">...</p>
# </sec>
# If we don't wrap p2 in a fake section, then the content orde§r would become
# main_sec: [p1, p3]
# sub_sec : [p2]
# By using the method below we will generated
# main_sec: [p1]
# sub_sec : [p2]
# wrap_sec: [p3]
def addContentsOrWrappedContents(sectionList, currentSection, contentsToBeAdded, level, shouldBeWrapped):
	if contentsToBeAdded==[]: return
	targetContents = currentSection['contents']
	if shouldBeWrapped:
		block_id[-1] = block_id[-1] + 1
		wid = build_id(block_id)
		subSection = {'implicit':True, 'level':level+1, 'id':wid, 'title':'', 'label':'' ,'tag':'wrap', 'contents':[]}
		sectionList.append(subSection)
		targetContents=subSection['contents']
		block_id.append(0)
	for content in contentsToBeAdded:
		block_id[-1] = block_id[-1] + 1
		content['id'] = build_id(block_id)
		targetContents.append(content)
	if shouldBeWrapped:
		block_id.pop()


def build_id(a):
	#print(a)
	id = ''
	for num in block_id: id += str(num) + '.'
	return id[0:-1]




# ------------------------------------------

def file_status_reset():
	file_status['name'] = ''
	file_status['errors'].clear()

def file_status_set_name(n):
	file_status['name'] = n

def file_status_add_error(r):
	file_status['errors'].append(r)

def file_status_ok():
	return len(file_status['errors'])==0

def file_status_print():
	msg = file_status['name'] + '\t'
	msg += str(len(file_status['errors'])) + '\t'
	for r in file_status['errors']: msg += r + '\t'
	print(msg)

# - - - - - - - - - - - - - - - - - - - - - - - -
# used by jsonpmc_httpserver.py
# - - - - - - - - - - - - - - - - - - - - - - - -
def parse_PMC_XML(xmlstr):
	return parse_PMC_XML_core(xmlstr,None, None)

# - - - - - - - - - - - - - - - - - - - - - - - -
# used by jsonpmc_httpserver.py
# - - - - - - - - - - - - - - - - - - - - - - - -
def getPmcFtpUrl(xmlstr):
	root = etree.fromstring(xmlstr)
	lnk = root.xpath('/OA/records/record/link')
	if lnk is not None and len(lnk) == 1: return lnk[0].get('href')
	return None

# - - - - - - - - - - - - - - - - - - - - - - - -

def parse_PMC_XML_core(xmlstr, root, input_file):
	if root is None:
		root = etree.fromstring(xmlstr)

	if input_file is None:
		input_file = '(unknown file name)'

	# (re)init stats variable
	file_status_reset()
	file_status_set_name(input_file)

	# (re)init global variable block_id used for building section / block ids
	block_id.clear()
	# (re)init output variable
	dict_doc = {}

	# Preprocessing tasks: simplify / clean up of the original xml
	# To be kept here before any parsing aimed at retrieving data
	for xs in root.xpath('//xref/sup'): xs.getparent().remove(xs)
	for sx in root.xpath('//sup/xref'): sx.getparent().remove(sx)
	etree.strip_tags(root,'sup')

	etree.strip_tags(root,'italic')
	etree.strip_tags(root,'bold')
	etree.strip_tags(root,'sub')
	etree.strip_tags(root,'ext-link')

	# rename this erroneous element
	for el in root.xpath('/article/floats-wrap'): el.tag='floats-group'

	etree.strip_elements(root, 'inline-formula','disp-formula', with_tail=False)
	#remove_subtree_of_elements(root,['inline-formula','disp-formula'])
	handle_supplementary_material_elements(root)
	handle_table_wrap_group_elements(root)
	handle_fig_group_elements(root)
	remove_embedding_group_elements(root,'fn')  # removes  fn-group wrapper (foot-notes)
	remove_embedding_group_elements(root,'app') # removes app-group wrapper (appendices)
	# End preprocessing


	# Now retrieve data from refactored XML
	dict_doc['affiliations'] = get_affiliations(root)
	dict_doc['authors'] = get_authors(root)

	# note: we use xref to retrieve author affiliations above this line

	etree.strip_tags(root,'xref')

	dict_doc['article_type'] = root.xpath('/article')[0].get('article-type')

	# note: we can get multiple journal-id elements with different journal-id-type attributes
	dict_doc['medline_ta'] = get_text_from_xpath(root, '/article/front/journal-meta/journal-id', False, True)

	dict_doc['journal'] = get_multiple_texts_from_xpath(root, '/article/front/journal-meta//journal-title', True)

	# note: I did not see any multiple <article-title> elements but we retrieve each element of the hypothetical list just in case
	#dict_doc['title'] = get_multiple_texts_from_xpath(root, '/article/front/article-meta/title-group/article-title', True)
	dict_doc['title'] = get_multiple_texts_from_xpath(root, '/article/front/article-meta/title-group', True)
	dict_doc['pmid'] = get_text_from_xpath(root, '/article/front/article-meta/article-id[@pub-id-type="pmid"]', True, False)
	dict_doc['doi'] = get_text_from_xpath(root, '/article/front/article-meta/article-id[@pub-id-type="doi"]', True, False)
	dict_doc['pmcid'] = get_text_from_xpath(root, '/article/front/article-meta/article-id[@pub-id-type="pmc"]', True, True)
	dict_doc['_id'] = dict_doc['pmcid']

	# ok with Julien, see precedence rules in def get_pub_date()
	dict_doc['publication_date'] = get_pub_date(root, 'd-M-yyyy')['date']
	dict_doc['publication_date_alt'] = get_pub_date(root, 'default format')['date'] # 'yyyy MMM d'
	dict_doc['pubyear'] = get_pub_date(root, 'yyyy')['date']
	dict_doc['publication_date_status']=get_pub_date(root, 'yyyy')['status']

	dict_doc['issue'] = get_text_from_xpath(root, '/article/front/article-meta/issue', True, False)
	dict_doc['volume'] = get_text_from_xpath(root, '/article/front/article-meta/volume', True, False)
	fp = get_text_from_xpath(root, '/article/front/article-meta/fpage', False, False)
	lp = get_text_from_xpath(root, '/article/front/article-meta/lpage', False, False)
	dict_doc['start_page'] = fp
	dict_doc['end_page'] = lp
	dict_doc['medline_pgn'] = build_medlinePgn(fp,lp)
	#dict_doc['abstract'] = get_abstract(root) -- should be obsolete now
	dict_doc['abstract'] = get_clean_text(root.find('front/article-meta/abstract'))
	dict_doc['keywords'] = get_keywords(root)

	# filling body, back and floats sections
	dict_doc['body_sections'] = []
	block_id.append(1)

	if dict_doc['title'] != '':
		dict_doc['body_sections'].append({
			'implicit':True, 'level':1, 'id':'1', 'label':'', 'title':'Title',
			'contents': [{'tag':'p', 'id':'1.1', 'text': dict_doc['title']}]})
		block_id[-1] = block_id[-1] + 1

	if dict_doc['abstract'] != '':
		abs_node = root.find('./front/article-meta/abstract')
		abs_title = etree.SubElement(abs_node, "title")
		abs_title.text = 'Abstract'
		sectionList = handle_section_flat(dict_doc['_id'], abs_node, 1, False, block_id)
		dict_doc['body_sections'].extend(sectionList)
		block_id[-1] = block_id[-1] + 1

	dict_doc['body_sections'].extend(get_sections(dict_doc['pmcid'], root.find('body')))
	dict_doc['float_sections']=get_sections(dict_doc['pmcid'], root.find('floats-group'))
	dict_doc['back_sections']=get_sections(dict_doc['pmcid'], root.find('back'))

	# for stats and debugging, can be commented
	dict_doc['figures_in_body']=len(root.xpath('/article/body//fig'))
	dict_doc['figures_in_back']=len(root.xpath('/article/back//fig'))
	dict_doc['figures_in_float']=len(root.xpath('/article/floats-group//fig'))
	dict_doc['tables_in_body']=len(root.xpath('/article/body//table'))
	dict_doc['tables_in_back']=len(root.xpath('/article/back//table'))
	dict_doc['tables_in_float']=len(root.xpath('/article/floats-group//table'))
	dict_doc['paragraphs_in_body']=len(root.xpath('/article/body//p'))
	dict_doc['paragraphs_in_back']=len(root.xpath('/article/back//p'))
	dict_doc['paragraphs_in_float']=len(root.xpath('/article/floats-group//p'))

	# for compatibility reasons
	dict_doc['pmcid']='PMC' + dict_doc['pmcid']
	dict_doc['_id'] = dict_doc['pmcid']

	return dict_doc

def get_sections(pmcid, node):
	if node is None: return []
	sections = handle_section_flat(pmcid, node, 1, True, block_id)
	block_id[-1] = block_id[-1] + 1
	return sections

# Recursively visits sub-elements of node.
# Sub-elements having a tag in kept_tags (i.e. fig, table, list) are left unchanged as well as their own sub-elements
# Other sub-elements are removed but their text / tail are attached to the appropriate sibling or embedding element.
def simplify_node(el, kept_tags, starting=True):
	if starting:
		for subel in el.iterchildren():
			simplify_node(subel, kept_tags, False)
	elif el.tag not in kept_tags: 	# we stringify this el
		trg_node = el.getprevious() if el.getprevious() is not None else el.getparent()
		trg_attr = 'tail' if el.getprevious() is not None else 'text'
		if el.text is not None: setattr(trg_node, trg_attr, (getattr(trg_node, trg_attr) or '') + el.text)
		for subel in el.iterchildren():
			el.addnext(subel)
			simplify_node(subel, kept_tags, False)
		if el.tail is not None: setattr(trg_node, trg_attr, (getattr(trg_node ,trg_attr) or '') + el.tail)
		el.getparent().remove(el)



# - - - - - - - - - - - - - - - - -
def main():
# - - - - - - - - - - - - - - - - -
	usage = "%prog file"
	parser = OptionParser()
	parser.add_option("-f","--file", dest="filename", help="Process one file for now")
	(options,args) = parser.parse_args()
	if len(args) < 1:
		sys.exit("Please provide a file")
	else:
		input_file = args[0]

	file_status_reset()
	file_status_set_name(input_file)
	print('------ ' + str(datetime.now()) + ' ' + input_file)
	xmlstr=get_file_content(input_file)
	root = etree.fromstring(xmlstr)

	lines = get_fig_parents(input_file,root)
	lines.extend(get_tw_parents(input_file,root))
	for l in lines: print(l)

	normal = True
	if normal:
		dict_doc = parse_PMC_XML_core(xmlstr,root,input_file)
		if len(dict_doc['body_sections'])<2: file_status_add_error("ERROR: no section after title")
		if not file_status_ok(): file_status_print()
		print(get_stats(input_file,root))
		print(get_body_structure(input_file,root))
		output_file='outfile'
		subdir='out'
		if 'pmcid' in dict_doc.keys():
			subdir = subdir + '/' + dict_doc['pmcid'][0:2]
			output_file = 'pmc'+ dict_doc['pmcid']
		if not os.path.exists(subdir):
			os.makedirs(subdir)
		output_file += '.json'
		out_file = codecs.open(subdir + '/' + output_file,'w','utf-8')
		out_file.write(json.dumps(dict_doc, sort_keys=True, indent=2))
		out_file.close()





# - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Tests (please ignore)
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test1():
	xmlstr="""
<root><p id="sec1">
The ecstasy of discovering a new hit from screening can lead to a highly productive research effort to discover new bioactive compounds. However, in too many cases this ecstasy is followed by the agony of realizing that the compounds are not active against the desired target. Many of these false hits are Pan Assay INterference compoundS (PAINS)
<sup>
<xref ref-type="bibr" rid="ref1">1</xref>
</sup>
or colloidal aggregators.
<sup>
<xref ref-type="bibr" rid="ref2">2</xref>
</sup>
Whether the screen is conducted in silico or in the laboratory and whether screening libraries, natural products, or drugs are used, all discovery efforts that rely on some form of screening to identify bioactivity are susceptible to this phenomenon. Studies that omit critical controls against experimental artifacts caused by PAINS may waste years of research effort as useless compounds are progressed.
<sup>
<xref ref-type="bibr" rid="ref3">3</xref>
−
<xref ref-type="bibr" rid="ref8">8</xref>
</sup>
The American Chemical Society (ACS) is eager to alert the scientific community to this problem and to recommend protocols that will eliminate the publication of research articles based on compounds with artificial activity. This editorial aims to summarize relevant concepts and to set the framework by which relevant ACS journals will address this issue going forward.
</p>
</root>
"""
	root = etree.fromstring(xmlstr)
	#etree.strip_tags(root,'xref')
	etree.strip_elements(root, 'sup', with_tail=False)
	#stuff=handle_paragrap('1111',root.find('p'))
	print(etree.tostring(root, pretty_print = True))
	#stuff=handle_xxx(root.find('p'))
	#print(json.dumps(stuff, sort_keys=True, indent=2))

def test2():
	parser = OptionParser()
	root = etree.XML('<root><some>stuff before</some><fig-group><caption><p>fg caption</p></caption><fig><caption><p>fig 1 caption</p></caption></fig><fig id="totofig"><caption><p>fig 2 caption</p>something else</caption></fig></fig-group>1-hi there<child><a href="toto">2-toto href</a></child>3-something normal<b>4-something in bold</b>some tail</root>')
	et = etree.ElementTree(root)
	with open('./pamori.xml', 'wb') as f:
		f.write(etree.tostring(et))
	handle_fig_group_elements(root)
	et = etree.ElementTree(root)
	with open('./pam.xml', 'wb') as f:
		f.write(etree.tostring(et))

def test3():
	parser = OptionParser()
	xmlstr='<root><p>p1</p><sec><title>s1</title><p>p2</p></sec><p>p3</p><p>p4</p><sec><title>s2</title><p>p5</p><p>p6</p></sec></root>'
	xmlstr='<root><sec><title>s1</title><p>p2</p></sec><sec><title>s2</title><p>p5</p><p>p6</p></sec></root>'
	xmlstr='<root><p>p1</p><p>p2</p><sec><title>s2</title><p>p5</p><p>p6</p></sec><p>petit dernier</p></root>'
	xmlstr='<root><p>p1</p><p>p2</p><p>petit dernier</p></root>'
	root = etree.fromstring(xmlstr)
	block_id.append(0)
	stuff=get_sections('111', root)
	print(json.dumps(stuff, sort_keys=True, indent=2))
	#parse_PMC_XML()

def test4():
	xmlstr="""
<root>
	<p>test before list 1
		<list list-type="simple" id="l1">
			<list-item><p>item 1.1</p></list-item>
			<list-item><p>item 1.2</p></list-item>
		</list>text after list 1 or before list 2
		<list list-type="simple" id="l2">
			<list-item><p>item 2.1</p></list-item>
			<list-item><p>item 2.2</p></list-item>
		</list></p>text after para
</root>
"""
	root = etree.fromstring(xmlstr)
	etree.strip_tags(root,'xref')
	etree.strip_elements(root, 'xref', with_tail=True)
	p = root.find('p')
	result = []
	result.append(clean_string(p.text))
	for l in p:
		for li in l:
			result.append(get_clean_text(li))
		result.append(clean_string(l.tail))
	result.append(clean_string(p.tail))
	print(result)
	print
	n=root.find(('p/list'))
	n.getparent().remove(n)
	print(etree.tostring(root, pretty_print=True))
	#print('p.text:' + p.text)
	#print('p.tail:' + p.tail)
	#stuff=handle_paragraph('1111',p)
	#print(json.dumps(stuff, sort_keys=True, indent=2))


def test5():
	xmlstr="""<root><p>c1<tag1>c2</tag1>c3<tag2>c4<tag21>c5</tag21>c6</tag2>c7<tag3>c8</tag3>c9<tag4>c10</tag4>c11</p></root>"""
	root = etree.fromstring(xmlstr)
	#tags_to_keep=set(['tag3'])
	node = root.find('p')
	#tags_to_strip=set()
	print(etree.tostring(root, pretty_print = True))
	kept_tags = sys.argv[1].split(',') if len(sys.argv)>1 else []
	print('kept tags: ' + str(kept_tags))
	simplify_node(node, kept_tags)
	print(etree.tostring(root, pretty_print = True))
	#stuff=handle_paragraph('1111',root.find('p'))
	#print(json.dumps(stuff, sort_keys=True, indent=2))

def test6():
	xmlstr="""<root>
	<pub-date pub-type="ppub">
		<day>24</day>
		<month>17</month>
		<year>2019</year>
		</pub-date>
</root>"""
	root = etree.fromstring(xmlstr)
	x = get_pub_date_by_type(root,'.//pub-date',None, 'd-M-yyyy')
	print(str(x['date']) + ' - ' + x['status'])
	x = get_pub_date_by_type(root,'.//pub-date',None, 'yyyy')
	print(str(x['date']) + ' - ' + x['status'])
	x = get_pub_date_by_type(root,'.//pub-date',None, None)
	print(str(x['date']) + ' - ' + x['status'])


# <mml:math id="M1" overflow="scroll">
# 	<mml:mi mathvariant="script">O</mml:mi>
# 	<mml:mo>(</mml:mo>
# 	<mml:mi>n</mml:mi>
# 	<mml:mo>log</mml:mo>
# 	<mml:mi>n</mml:mi>
# 	<mml:mo>)</mml:mo>
# </mml:math>

# OK
# <mml:math id="M1" overflow="scroll">
# 	<mml:mi mathvariant="script">O</mml:mi>
# 	<mml:mo>(</mml:mo>
# 	<mml:mi>n</mml:mi>
# 	<mml:mo>log</mml:mo>
# 	<mml:mi>n</mml:mi>
# 	<mml:mo>)</mml:mo>
# </mml:math>

def test():
	xmlstr="""<root xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:mml="http://www.w3.org/1998/Math/MathML"><p>
	Crochemore’s repetitions algorithm, also referred to as Crochemore’s partitioning algorithm, was introduced in 1981, and was the first optimal
	<inline-formula>
	<mml:math id="M1" overflow="scroll">
		<mml:mi mathvariant="script">O</mml:mi>
		<mml:mo>(</mml:mo>
		<mml:mi>n</mml:mi>
		<mml:mo>log</mml:mo>
		<mml:mi>n</mml:mi>
		<mml:mo>)</mml:mo>
	</mml:math>
	</inline-formula>
	-time algorithm to compute all repetitions in a string of length
	<italic>n</italic>
	. </p></root>"""
	root = etree.fromstring(xmlstr)
	thing = root.xpath('p')
	print('type:')
	print(type(thing))
	x = get_clean_text(thing)
	print(x)





# - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# globals
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
file_status = {'name':'', 'errors':[]}
block_id=[]

if __name__ == '__main__':
	test()
	#main()
