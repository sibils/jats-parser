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
	mmm=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
	# possible pubtype: epub, pmc-release, ppub, otherwise first whatever its type
	if not pubtype is None:
		selector += '[@pub-type="' + pubtype + '"]'
	day=''
	month=''
	year=''
	dates = someroot.xpath(selector);
	if len(dates)>0:
		dt = dates[0]
		years = dt.xpath('year')
		if len(years)>0:
			year = years[0].text
			months = dt.xpath('month')
			if len(months)>0:
				mm=months[0].text
				if mm.isdigit():
					if int(mm)<=12:
						month=mmm[int(mm)-1]
				days = dt.xpath('day')
				if len(days)>0:
					day=days[0].text
	#print('y m d:' + year + '/' + month + '/' + day)
	if len(year)>0 and len(month)>0 and len(day)>0:
		if format=='yyyy': return year
		if format=='d-M-yyyy': return day + '-' + mm + '-' + year
		return year + ' ' + month + ' ' + day
	if len(year)>0 and len(month)>0:
		if format=='yyyy': return year
		if format=='d-M-yyyy': return mm + '-' + year
		return year + ' ' + month
	elif len(year)>0:
		return year
	else:
		return None

def get_pub_date(someroot,format):
	# possible pubtype: epub, pmc-release, ppub, otherwise first whatever its type
	# the precedence order can be changed here
	selector = '/article/front/article-meta/pub-date'
	dt = get_pub_date_by_type(someroot, selector, 'epub', format)
	if dt is None: dt = get_pub_date_by_type(someroot, selector, 'ppub', format)
	if dt is None: dt = get_pub_date_by_type(someroot, selector, 'pmc-release', format)
	if dt is None: dt = get_pub_date_by_type(someroot, selector, None, format)
	if dt is None:
		file_status_add_error('ERROR, element not found: ' + selector)
	else:
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

def clean_string(s):
	# replaces new line, unbreakable space, TAB with SPACE and strip the final string
	return s.replace('\n', ' ').replace(u'\u00a0', ' ').replace('\t', ' ').strip()


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
			'label': label, 'caption': caption,
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
	sm_list = someroot.xpath('//supplementary-material')
	if sm_list is None: return
	for sm in sm_list:
		for tw in sm.iterchildren('table-wrap'):
			sm.addprevious(tw)

		# After moving <table-wrap> elements try build a figure obj with the remaining content if any
		# Note: we create a figure but if can be a table as well...
		label=get_clean_text(sm.find('label'))
		caption=get_clean_text(sm.find('caption'))
		media=[ get_xlink_href(m) for m in sm.xpath('media') ]
		graph=[ get_xlink_href(g) for g in sm.xpath('graphic') ]
		if (label != '' or caption != '') and (len(media)>0 or len(graph)>0):
			fig = etree.SubElement(sm.getparent(), 'fig')
			fig.attrib['id']='' # there is a special handling of figure with no id
			etree.SubElement(fig,'label').text=label
			etree.SubElement(fig,'caption').text=caption
			for m in media: etree.SubElement(fig,'media').attrib['href']=m
			for g in graph: etree.SubElement(fig,'graphic').attrib['href']=g

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

# a paragraph <p> may contain <fig> and / or <table-wrap> elements.
# if this is the case figs & tables are extracted from the paragraph, parsed with their own handler
# and appended as additional contents in the content list returned
def handle_paragraph(pmcid,el):
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

# recursive function used to parse the article body.
# the body tree is traversed depth first:
# on encountering a section <sec> element, the function calls itself
# on encountering <p>, <fig> and <table-wrap> elements, dedicated handlers are called
# on encountering another element, a default handler is used
def handle_body_section_flat(pmcid, sec, level, implicit, block_id):

	sectionList = []
	id = ''.join(sec.xpath('@id'))
	title = ''.join(sec.xpath("title/text()"))
	label = ''.join(sec.xpath("label/text()"))
	mainSection = {'implicit':implicit, 'level': level, 'id': build_id(block_id),
		'title': clean_string(coalesce(title,'')),
		'label': clean_string(coalesce(label,'')),
		'contents':[]}
	# we add main section to the list before any other sub sections
	sectionList.append(mainSection)
	# print(indent(level) + 'level: ' + str(level) + ' - name: ' + mainSection['name'])
	block_id.append(0)
	for el in sec:

		# recursive call for any embedded section
		if el.tag == 'sec':
			block_id[-1] = block_id[-1] + 1
			sectionList.extend(handle_body_section_flat(pmcid, el, level + 1, False, block_id))

		# ignore elements handled elsewhere or that are unnecessary
		elif el.tag == 'title':
			continue
		elif el.tag == 'label':
			continue
		elif isinstance(el,etree._Comment):
			continue

		# returns paragraph content plus any embedded figures or tables as sibling contents
		elif el.tag == 'p':
			contentList = handle_paragraph(pmcid, el)
			for content in contentList:
				block_id[-1] = block_id[-1] + 1
				content['id'] = build_id(block_id)
				mainSection['contents'].append(content)

		# handle figures that are child of <body> or <sec>
		elif el.tag == 'fig':
			content = handle_fig(pmcid, el)
			block_id[-1] = block_id[-1] + 1
			content['id'] = build_id(block_id)
			mainSection['contents'].append(content)

		# handle tables that are child of <body> or <sec>
		elif el.tag == 'table-wrap':
			content = handle_table_wrap(pmcid,el)
			block_id[-1] = block_id[-1] + 1
			content['id'] = build_id(block_id)
			mainSection['contents'].append(content)

		# default handler: just keep tag and get all text
		else:
			content = {'tag': el.tag, 'text': clean_string(' '.join(el.itertext()))}
			block_id[-1] = block_id[-1] + 1
			content['id'] = build_id(block_id)
			mainSection['contents'].append(content)

	block_id.pop()
	return sectionList


def build_id(a):
	#print(a)
	id = ''
	for num in block_id: id += str(num) + '.'
	return id[0:-1]

def print_section(s):
	print (indent(s['level']) + input_file + ':' + str(s['level']) + ' - ' + s['name'])
	for content in s['contents']:
		shorttext = content['text'][0:40] + '...' + content['text'][-40:]
		print( indent(s['level']+1) + content['tag'] + ' - ' + shorttext )

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

def parse_PMC_XML(xmlstr):
	return parse_PMC_XML_core(xmlstr,None, None)

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

	# Preprocessing tasks: simplify / clean up of the original xml
	# To be kept here before any parsing aimed at retrieving data
	etree.strip_tags(root,'italic')
	etree.strip_elements(root, 'inline-formula','disp-formula', with_tail=False)
	#remove_subtree_of_elements(root,['inline-formula','disp-formula'])
	handle_supplementary_material_elements(root)
	handle_table_wrap_group_elements(root)
	handle_fig_group_elements(root)
	handle_boxed_text_elements(root)
	# End preprocessing


	# (re)init output variable
	dict_doc = {}

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
	dict_doc['title'] = get_multiple_texts_from_xpath(root, '/article/front/article-meta/title-group/article-title', True)

	dict_doc['pmid'] = get_text_from_xpath(root, '/article/front/article-meta/article-id[@pub-id-type="pmid"]', True, False)
	dict_doc['doi'] = get_text_from_xpath(root, '/article/front/article-meta/article-id[@pub-id-type="doi"]', True, False)
	dict_doc['pmcid'] = get_text_from_xpath(root, '/article/front/article-meta/article-id[@pub-id-type="pmc"]', True, True)
	dict_doc['_id'] = dict_doc['pmcid']

	dict_doc['publication_date_alt'] = get_pub_date(root, 'd-M-yyyy')
	dict_doc['publication_date'] = get_pub_date(root, 'default format') # 'yyyy MMM d'
	dict_doc['pubyear'] = get_pub_date(root, 'yyyy')
	dict_doc['issue'] = get_text_from_xpath(root, '/article/front/article-meta/issue', True, False)
	dict_doc['volume'] = get_text_from_xpath(root, '/article/front/article-meta/volume', True, False)
	fp = get_text_from_xpath(root, '/article/front/article-meta/fpage', False, False)
	lp = get_text_from_xpath(root, '/article/front/article-meta/lpage', False, False)
	dict_doc['start_page'] = fp
	dict_doc['end_page'] = lp
	dict_doc['medline_pgn'] = build_medlinePgn(fp,lp)
	dict_doc['abstract'] = get_abstract(root)
	dict_doc['keywords'] = get_keywords(root)

	sections = []
	block_id.append(1)

	if dict_doc['title'] != '':
		sections.append({'implicit':True, 'level':1, 'id':'1', 'label':'', 'title':'Title', 'contents': [{'tag':'p', 'id':'1.1', 'text': dict_doc['title']}]})
		block_id[-1] = block_id[-1] + 1
	if dict_doc['abstract'] != '':
		sections.append({'implicit':True, 'level':1, 'id':'2', 'label':'', 'title':'Abstract', 'contents': [{'tag':'p', 'id':'2.1', 'text': dict_doc['abstract']}]})
		block_id[-1] = block_id[-1] + 1
	dict_doc['sections'] = sections

	body=root.find('body')
	if body is not None:
		non_sec_body_children = body.iterchildren(['p', 'fig', 'table-wrap'])
		weHaveContentOutOfSections = sum(1 for el in non_sec_body_children) > 0
		if weHaveContentOutOfSections:
			implicitSec = body
			sectionList = handle_body_section_flat(dict_doc['_id'], implicitSec, 1, True, block_id)
			block_id[-1] = block_id[-1] + 1
			dict_doc['sections'].extend(sectionList)
		else:
			for sec in root.xpath('/article/body/sec'):
				sectionList = handle_body_section_flat(dict_doc['_id'], sec, 1, False, block_id)
				block_id[-1] = block_id[-1] + 1
				dict_doc['sections'].extend(sectionList)

	return dict_doc


# ------------------------------------------

def getPmcFtpUrl(xmlstr):
	root = etree.fromstring(xmlstr)
	lnk = root.xpath('/OA/records/record/link')
	if lnk is not None and len(lnk) == 1: return lnk[0].get('href')
	return None

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
		if len(dict_doc['sections'])<2: file_status_add_error("ERROR: no section after title")
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


# - - - - - - - - - - - - - - - - - - -
# ignore this, for test purpose only
# - - - - - - - - - - - - - - - - - - -
def test():
	parser = OptionParser()
	root = etree.XML('<root><some>stuff before</some><fig-group><caption><p>fg caption</p></caption><fig><caption><p>fig 1 caption</p></caption></fig><fig id="totofig"><caption><p>fig 2 caption</p>something else</caption></fig></fig-group>1-hi there<child><a href="toto">2-toto href</a></child>3-something normal<b>4-something in bold</b>some tail</root>')
	et = etree.ElementTree(root)
	with open('./pamori.xml', 'wb') as f:
		f.write(etree.tostring(et))
	handle_fig_group_elements(root)
	et = etree.ElementTree(root)
	with open('./pam.xml', 'wb') as f:
		f.write(etree.tostring(et))

# - - - - - - -
# globals
# - - - - - - -
file_status = {'name':'', 'errors':[]}
block_id=[]

if __name__ == '__main__':
	#test()
	main()
