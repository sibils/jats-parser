# Pam April 2019
# Parsing jats DTD, the standard for Europe PMC
# see https://jats.nlm.nih.gov/

import sys
import os
from os.path import join, getsize
import glob
from optparse import OptionParser
import shutil

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
		input_dir = args[0]
		output_dir = args[1]

	print("get subdirectories of " + input_dir)
	print("target directory is  " + output_dir)

	for root,dirs,files in os.walk(input_dir):
		reldir=root[len(input_dir):]
		print(root,reldir,dirs,files)
		if len(files) > 0:
			newdirs = output_dir + '/' + reldir
			if not os.path.exists(newdirs):
				print ('Making dirs  ' + newdirs)
				os.makedirs(newdirs)
		for f in files[0:10]:
			if f[-3:]=='xml':
				oldname = root + '/' + f
				newname = newdirs + '/' + f
				print ('Copying ' + oldname + ' to ' + newname)
				shutil.copy(oldname, newname)

	print('Done')

	return



if __name__ == '__main__':
	main()
