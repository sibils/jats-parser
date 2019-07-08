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

def get_cardinality(n):
	if n>1: return 'N'
	return str(n)

def get_el_cardinality(someroot, somepath):
	c = get_cardinality(len(someroot.xpath(somepath)))
	return somepath + ':' + c

def get_stats(fname, someroot):
	line = 'pam-stats' + '\t'
	line += fname + '\t'
	line += get_el_cardinality(someroot,'/article/front/article-meta/abstract') + '\t'
	line += get_el_cardinality(someroot,'/article/body/p') + '\t'
	line += get_el_cardinality(someroot,'/article/body/sec')
	return line

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
		result.append(clean_string(' '.join([t for t in k.itertext()])))
	return result

def get_multiple_texts_from_xpath(someroot, somepath, withErrorOnNoValue):
	result = ''
	x = someroot.xpath(somepath)
	if len(x) >= 1:
		result = clean_string(' '.join([el.text for el in x]))
	elif withErrorOnNoValue is True:
		file_status_add_error("ERROR, element not found: " + somepath)
	return result

def get_text_from_xpath(someroot, somepath, withWarningOnMultipleValues, withErrorOnNoValue):
	result = ''
	x = someroot.xpath(somepath)
	if len(x) >= 1:
		result = x[0].text
		if len(x) > 1 and withWarningOnMultipleValues is True :
			file_status_add_error('WARNING: multiple elements found: ' + somepath)
	elif withErrorOnNoValue is True:
		file_status_add_error("ERROR, element not found: " + somepath)
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
	affs = someroot.xpath('/article/front/article-meta/contrib-group/aff')
	for aff in affs:
		id=aff.get('id')
		label=''
		for el in aff.iterchildren('label'):
			if el.tag=='label' : label = el.text
		name = clean_string( ''.join( aff.itertext(['aff','institution','country']) ) )
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
			elif el.tag == 'xref' and el.get('ref-type')=='aff':
				if el.get('rid') != None: affiliation_list.append(el.get('rid'))

		author = {}
		author['affiliation_list'] = affiliation_list
		author['lastName'] = surname
		author['firstName'] = givennames
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
	# replaces new line, unbreakable space, TAB with SPACE and strip the fial string
	return s.replace('\n', ' ').replace(u'\u00a0', ' ').replace('\t', ' ').strip()


def get_abstract(someroot):
	x = someroot.xpath('/article/front/article-meta/abstract')
	content=''
	for xi in x:
		content += ' '.join(xi.itertext()) + ' '
	return clean_string(content)

def indent(level):
	spaces = ''
	for i in range(1,level): spaces += '  '
	return spaces

def do_nothing():
	return

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



def handle_table_wrap(pmcid, tw):
	# table label
	label = ''
	label_node = tw.find('label')
	if label_node is not None: label = label_node.text or ''
	# table caption
	caption = ''
	caption_node = tw.find('caption/p')
	if caption_node is None: caption_node = tw.find('caption/title')
	if caption_node is not None:
		caption = clean_string(' '.join(caption_node.itertext()))
	# table content
	columns=[]
	row_values=[]
	table_tree = tw.find('table')
	if table_tree is None: table_tree = tw.find('alternatives/table')
	if table_tree is not None:
		table_xml = etree.tostring(table_tree)
		#columns, row_values = table_to_df(table_xml)
	return {'tag': 'table', 'label': label,
			'caption': caption,
			'table_columns': columns,
			'table_values': row_values}


# modifies the original XML by
# 1. adding <fig-group> caption text to each child <fig> element caption
# 2. moving <fig> elements next to their embedding <fig-group>
# 3. removing <fig-group> handle_fig_group_elements
def handle_fig_group_elements(someroot):
	fg_list = someroot.xpath('//fig-group')
	if fg_list is None: return
	for fg in fg_list:
		# store fig-group caption
		fg_captions=[]
		for fgc in fg.iterchildren('caption'):
			fg_captions.append(' '.join(fgc.itertext()))
		for fig in fg.xpath('fig'):
			# concat fig-group ad fig captions
			captions=[]
			captions.extend(fg_captions)
			cpt = fig.find('caption')
			if (cpt is not None): captions.append(' '.join(cpt.itertext()))
			caption = clean_string(' '.join(captions))
			# rebuild fig caption element with new content
			for fc in fig.iterchildren('caption'): fig.remove(fc)
			new_caption = etree.SubElement(fig, 'caption')
			new_caption.text = caption
			# moves fig as the previous sibling of fig-group
			fg.addprevious(fig)
		# removes fig-group which is now unnecesssary
		fg.getparent().remove(fg)

def handle_fig(pmcid, fig):
	fig_id = fig.attrib['id']

	fig_label = ''
	lbl = fig.find('label')
	if (lbl is not None): fig_label = clean_string(' '.join(lbl.itertext()))

	captions=[]
	parent = fig.getparent()
	if (parent.tag=='fig-group'):
		for pc in parent.iterchildren('caption'):
			captions.append(' '.join(cpt.itertext()))
	cpt = fig.find('caption')
	if (cpt is not None): captions.append(' '.join(cpt.itertext()))
	caption = clean_string(' '.join(captions))

	img_src='notfound.jpg'
	graphic = fig.find('graphic')
	if graphic is not None:
		href = graphic.get('{http://www.w3.org/1999/xlink}href')
		if href is not None:
			img_src = 'https://europepmc.org/articles/PMC' + pmcid + '/bin/' + href + '.jpg'

	return {'tag':'fig', 'text': caption, 'fig_id': fig_id, 'label': fig_label, 'img_src': img_src}

def handle_paragraph(pmcid,el):
	contentList=[]
	#subs = el.xpath([]'fig','table-wrap')
	#if subs is not None:
	for sub_el in el.iterchildren(['fig','table-wrap']):
		if sub_el.tag == 'fig':
			contentList.append(handle_fig(pmcid,sub_el))
		elif sub_el.tag == 'table-wrap':
			contentList.append(handle_table_wrap(pmcid,sub_el))
		sub_el.getparent().remove(sub_el)

	content = {'tag': el.tag, 'text': clean_string(' '.join(el.itertext()))}
	contentList.insert(0,content)

	return contentList

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
		if el.tag == 'sec':
			block_id[-1] = block_id[-1] + 1
			sectionList.extend(handle_body_section_flat(pmcid, el, level + 1, False, block_id))
		elif el.tag == 'title':
			continue
		elif el.tag == 'label':
			continue
		elif isinstance(el,etree._Comment):
			continue
		elif el.tag == 'p': # returns paragraph content item and embedded figures as siblings
			contentList = handle_paragraph(pmcid, el)
			for content in contentList:
				block_id[-1] = block_id[-1] + 1
				content['id'] = build_id(block_id)
				mainSection['contents'].append(content)

		elif el.tag == 'fig':  # handle figures that are child of <body> or <sec>
			content = handle_fig(pmcid, el)
			block_id[-1] = block_id[-1] + 1
			content['id'] = build_id(block_id)
			mainSection['contents'].append(content)

		elif el.tag == 'table-wrap':
			content = handle_table_wrap(pmcid,el)
			block_id[-1] = block_id[-1] + 1
			content['id'] = build_id(block_id)
			mainSection['contents'].append(content)

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

def file_status_init():
	return {'name':'', 'errors':[]}

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
	return parse_PMC_XML_core(xmlstr,None)

def parse_PMC_XML_core(xmlstr, root):
	if root is None:
		root = etree.fromstring(xmlstr)

	etree.strip_tags(root,'italic')
	handle_fig_group_elements(root)
	handle_boxed_text_elements(root)

	dict_doc = {}
	dict_doc['affiliation_list'] = get_affiliations(root)
	dict_doc['author_list'] = get_authors(root)

	# note: we use xref to retrieve author affiliations above this line
	etree.strip_tags(root,'xref')

	dict_doc['articleType'] = root.xpath('/article')[0].get('article-type')

	# note: we can get multiple journal-id elements with different journal-id-type attributes
	dict_doc['medlineTA'] = get_text_from_xpath(root, '/article/front/journal-meta/journal-id', False, True)

	dict_doc['journal'] = get_multiple_texts_from_xpath(root, '/article/front/journal-meta/journal-title-group/journal-title', True)

	# note: I did not see any multiple <article-title> elements but we retrieve each element of the hypothetical list just in case
	dict_doc['full_title'] = get_multiple_texts_from_xpath(root, '/article/front/article-meta/title-group/article-title', True)

	dict_doc['pmid'] = get_text_from_xpath(root, '/article/front/article-meta/article-id[@pub-id-type="pmid"]', True, False)
	dict_doc['doi'] = get_text_from_xpath(root, '/article/front/article-meta/article-id[@pub-id-type="doi"]', True, False)
	dict_doc['pmcid'] = get_text_from_xpath(root, '/article/front/article-meta/article-id[@pub-id-type="pmc"]', True, True)
	dict_doc['_id'] = dict_doc['pmcid']

	dict_doc['publication_date_alt'] = get_pub_date(root, 'd-M-yyyy')
	dict_doc['publication_date'] = get_pub_date(root, 'default format') # 'yyyy MMM d'
	dict_doc['publication_year'] = get_pub_date(root, 'yyyy')
	dict_doc['issue'] = get_text_from_xpath(root, '/article/front/article-meta/issue', True, False)
	dict_doc['volume'] = get_text_from_xpath(root, '/article/front/article-meta/volume', True, False)
	fp = get_text_from_xpath(root, '/article/front/article-meta/fpage', False, False)
	lp = get_text_from_xpath(root, '/article/front/article-meta/lpage', False, False)
	dict_doc['startPage'] = fp
	dict_doc['endPage'] = lp
	dict_doc['medlinePgn'] = build_medlinePgn(fp,lp)
	dict_doc['abstract'] = get_abstract(root)
	dict_doc['keywords'] = get_keywords(root)
	sections = []
	block_id.append(1)
	sections.append({'implicit':True, 'level':1, 'id':'1', 'name':'Title', 'contents': [{'tag':'p', 'id':'1.1', 'text': dict_doc['full_title']}]})
	block_id[-1] = block_id[-1] + 1
	if dict_doc['abstract'] != '':
		sections.append({'implicit':True, 'level':1, 'id':'2', 'name':'Abstract', 'contents': [{'tag':'p', 'id':'2.1', 'text': dict_doc['abstract']}]})
		block_id[-1] = block_id[-1] + 1
	dict_doc['sections'] = sections

	non_sec_body_children = root.xpath('/article/body')[0].iterchildren(['p', 'fig', 'table-wrap'])
	weHaveContentOutOfSections = sum(1 for el in non_sec_body_children) > 0
	#weHaveContentOutOfSections = len(root.xpath('/article/body/p'))>0
	if weHaveContentOutOfSections:
		implicitSec = root.xpath('/article/body')[0]
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

	file_status_init()
	file_status_set_name(input_file)
	print('------ ' + str(datetime.now()) + ' ' + input_file)

	xmlstr=get_file_content(input_file)
	root = etree.fromstring(xmlstr)

	normal = True

	lines = get_fig_parents(input_file,root)
	lines.extend(get_tw_parents(input_file,root))
	for l in lines: print(l)


	if normal:
		dict_doc = parse_PMC_XML_core(xmlstr,root)
		if len(dict_doc['sections'])<2: file_status_add_error("ERROR: no section after title")
		if not file_status_ok(): file_status_print()

	if normal:
		print(get_stats(input_file,root))

	if normal:
		print(get_body_structure(input_file,root))



	if normal:
		output_file='outfile'
		subdir='out'
		if 'pmcid' in dict_doc.keys():
			subdir = subdir + '/' + dict_doc['pmcid'][0:2]
			output_file = 'pmc'+ dict_doc['pmcid']
		# if 'pmid' in dict_doc.keys():
		# 	output_file += '_PMID'+dict_doc['pmid']
		if not os.path.exists(subdir):
			os.makedirs(subdir)
		output_file += '.json'
		out_file = codecs.open(subdir + '/' + output_file,'w','utf-8')
		out_file.write(json.dumps(dict_doc, sort_keys=True, indent=2))
		out_file.close()


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

# 	x = ' '.join(root.itertext())
#	 	for el in root.iter():
# 		print(el.tag)
# 		print(el.text)
# 	print('now everything:')
 	#print(root)
	# does not respect order as we would like
	# for el in root.iter("*"):
	# 	print(el.tag)
	# 	if not el.text is None: print(el.text)
	# 	if not el.tail is None: print(el.tail)


# - - - - - - -
# globals
# - - - - - - -

block_id=[]

file_status = file_status_init()

if __name__ == '__main__':
	#test()
	main()
