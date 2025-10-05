import numpy as np
from math import *
import requests
import statistics
from PIL import Image, ImageFont, ImageDraw 
from datetime import date, datetime, timedelta
import contextlib
#from pygifsicle import optimize
#import subprocess
import time
import dropbox
import os.path
import dropbox_client

auto = True
download = True
average = False
minimum = False

year = 2025;
enddate = datetime(2024,6,1)

windows = [5,3,1]
frames = 10
threshold = 20;
path = './'
prefix = 'asi-AMSR2-n3125-'
suffix = '-v5.4_visual'
#https://seaice.uni-bremen.de/data/amsr2/asi_daygrid_swath/n3125/2021/aug/Arctic3125/
allvalues = [];
extent = 0;
monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
monthLengths = [31,28,31,30,31,30,31,31,30,31,30,31]
leftrow = 340
rightrow = 1010
topcol = 770
bottomcol = 1440
caa = False

def padzeros(x,n=2):
	if(n == 3):
		return str(x) if x >= 100 else '0'+str(x) if x >= 10 else '00' + str(x)
	elif(n == 2):
		return str(x) if x >= 10 else '0'+str(x)

def getfilename(date, orig=False):
	daystring = str(date.day) if date.day >= 10 else '0' + str(date.day);
	return prefix + str(date.year) + ('0' if date.month < 10 else '') + str(date.month) + daystring + suffix + ('' if orig else '_bis') + '.png'
	
def getmedianfilename(startdate, enddate, caa = False):
	return path + getAverageType() + '_' + getDateIsoString(startdate) + '_to_' + getDateIsoString(enddate) + ('caa' if caa else '') + '.png'

def getAverageType():
	return "mean" if average else "minimum" if minimum else "median"
	
def getDateIsoString(date):
	 return str(date.year) + str(padzeros(date.month)) + str(padzeros(date.day))

def downloadimage(date):
	filename = getfilename(date, True)
	localFileName = path + 'original/' + filename
	if not os.path.isfile(localFileName):
		monthnames = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']
		folder = 'https://seaice.uni-bremen.de/data/amsr2/asi_daygrid_swath/n3125/' + str(date.year) + '/' + str(monthnames[date.month-1]) + '/Arctic3125/'							
		file_object = requests.get(folder + filename)
		if(file_object.status_code == 404):
			print('nonexistent file ' + folder + filename)
		else:		
			print('downloaded file ' + filename)
		with open(localFileName, 'wb') as local_file:
			local_file.write(file_object.content)
	im = Image.open(localFileName)
	rgb_im = im.convert('RGBA')
	localFileNameBis = path + 'original/' + getfilename(date)	
	# Save the converted image
	rgb_im.save(localFileNameBis)

def getvalue(pixel):
	if(pixel[0] == 0 and pixel[1] == 220 and pixel[2] == 0): # land
		return -2;
	elif(pixel[0] == 180 and pixel[1] == 180 and pixel[2] == 255): # ocean
		return 0;
	elif(abs(pixel[0] - pixel[1]) < threshold and abs(pixel[1] - pixel[2]) < threshold): # grey
		return 127 + int(round(pixel[0]/2));	
	elif(pixel[0] < threshold and pixel[1] < threshold and pixel[2] <= 127 + threshold): # blue
		return 127 - int(round(pixel[2]/2));	
	elif(abs(pixel[0] - pixel[1]) < threshold and pixel[0] <= 127 + threshold and pixel[2] >= 127 - threshold and abs(pixel[2]-pixel[0]-127) < threshold): # blue
		return 127 - int(round(pixel[2]/2));	
	return -1;

def getcolor(value):
	if(value >= 127):
		x = 2*(value - 127);
		return (x,x,x,255);
	elif(value >= 63):
		x = 2*(127 - value)
		return (0,0,x,255);
	elif(value > 0):
		x = 2*(127 - value)
		y = 2*(63 - value);
		return (y,y,x,255);
	elif(value == 0):
		return(180,180,255,255);

shiftrow = -21
shiftcol = 34
		
def processday(date, printmatrix, width, height):
	global extent
	print('process day', date)
	
	if(download):
		downloadimage(date)
		#return
	
	filename = path + 'original/' + getfilename(date)
	im = Image.open(filename)
	matrix = im.load()
	
	copyim = im.crop((leftrow-shiftrow,topcol-shiftcol,rightrow-shiftrow,bottomcol-shiftcol))
	copyim.save(filename[0:-4] + '_copy.png')
	thewidth, theheight = im.size
	copywidth, copyheight = copyim.size
	for row in range(width):
		for col in range(height):
			if(row < leftrow-shiftrow or row > rightrow-shiftrow or col < topcol-shiftcol or col > bottomcol-shiftcol):
				continue;
			pixel = matrix[row,col];
			value = getvalue(pixel);
						
			if(value > 37):
				extent += 1
			printpixel = printmatrix[row,col];				
			
			if(not(value in allvalues)):
				allvalues.append(value);
				allvalues.sort();
				
			if(value >= 0):
				if(printpixel[3] == 255):
					printpixel = (253,253,253,253);				
				printmatrix[row,col] = (value, printpixel[0], printpixel[1], printpixel[2]); #int(round((printpixel + value)/2))

def makeTopWhite(printmatrix, width, height):
	for row in range(width):
		for col in range(height):
			printpixel = printmatrix[row,col];
			if(col < topcol-shiftcol+50):
				printmatrix[row,col] = (255,255,255,255)
			
def printmedian(enddate, printmatrix, width, height):
	print('inside print median')
	filename = path + 'original/' + getfilename(enddate)
	endim = Image.open(filename)
	endmatrix = endim.load()

	copyim = endim.crop((leftrow-shiftrow,topcol-shiftcol,rightrow-shiftrow,bottomcol-shiftcol))
	copyim.save(filename[0:-4] + '_copy.png')

	for row in range(width):
		for col in range(height):
			printpixel = printmatrix[row,col];
			if(col < topcol-shiftcol+50):
				printmatrix[row,col] = (255,255,255,255)
				continue
			if(printpixel[3] == 256):
				printmatrix[row,col] = (printpixel[0],printpixel[1],printpixel[2],255);
			else:				
				endpixel = endmatrix[row,col];
				endvalue = getvalue(endpixel);		
				
				if(not(endvalue in allvalues)):
					allvalues.append(endvalue);
					allvalues.sort();
				
				if(endvalue <= -1):
					printmatrix[row,col] = endpixel;
					continue;
				list = [];
				list.append(endvalue);
					
				j = 0
				while j <= 3 and printpixel[j] >= 0 and printpixel[j] != 253:
					list.append(printpixel[j]);
					j += 1;					
				median = int(round(sum(list)/len(list))) if average else int(round(min(list))) if minimum else int(round(statistics.median(list)));
				printmatrix[row,col] = getcolor(median);

def contains(list, pixel):
    for x in list:
        if x[0] == pixel[0] and x[1] == pixel[1] and x[2] == pixel[2]:
            return True
    return False

def generateMedian(startdate, enddate, window, caa = False):
	if(download):
		downloadimage(enddate)
	printim = Image.open(path + 'original/' + getfilename(enddate))
	printmatrix = printim.load()
	width, height = printim.size

	indexed = np.array(printim)
	#palette = printim.getpalette()
	#print('pallette', palette)
	#print('width: ' + str(width) + ', height: ' + str(height))	
	#extent = 0;

	date = startdate

	while date < enddate:
		processday(date, printmatrix, width, height)
		date = date + timedelta(days = 1)
	if window > 1:
		printmedian(enddate,printmatrix, width, height)
	else:
		makeTopWhite(printmatrix, width, height)

	printim = printim.crop((leftrow-shiftrow,topcol-shiftcol,rightrow-shiftrow,bottomcol-shiftcol))

	printimtext = ImageDraw.Draw(printim)
	fontsize=40 if minimum else 43
	labelindent=429
	font = ImageFont.truetype("arialbd.ttf", fontsize)
	title = str(window) +"-day " + getAverageType() + ' ' + str(startdate.day) + "-" + str(enddate.day) + " " + str(monthNames[startdate.month-1]) + " " + str(enddate.year)
	if enddate.month != startdate.month:
		title = str(window) +"-day " + getAverageType() + ' ' + str(startdate.day) + "/" + str(startdate.month) + " - " + str(enddate.day) + "/" + str(enddate.month) + " " + str(enddate.year)
	if window == 1:
		title = str(enddate.day) + " " + str(monthNames[enddate.month-1]) + " " + str(enddate.year)
		
	printimtext.text((1,1), title, (0, 0, 0), font=font)

	printim.save(getmedianfilename(startdate, enddate, caa), quality=25, optimize = True, compress_level=9)
	#print(extent)	
	
def makeAnimation(enddate, window, caa = False):
	print('inside make animation', enddate, window)
	date = enddate - timedelta(days = frames)
	filenames = []
	endpause = 4
	for k in range(frames):	
		date = date + timedelta(days = 1)
		startdate = date - timedelta(days = window-1)
		localfilename = getmedianfilename(startdate, date, caa)
		filenames.append(localfilename)
	print(filenames)
	lastfilename = filenames[-1]
	for k in range(endpause):
		filenames.append(lastfilename)
	with contextlib.ExitStack() as stack:
		imgs = (stack.enter_context(Image.open(f)) for f in filenames)
		img = next(imgs)
		# https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#gif
		startdate = enddate - timedelta(days = window-1+frames-1)
		filename = path + 'animation_bremen_' + str(window) + '_day_' + getAverageType() + '_' + getDateIsoString(startdate) + '_to_' + getDateIsoString(enddate) + '.gif'
		if auto:
			filename = path + 'animation_bremen_' + str(window) + '_day_' + getAverageType() + '_latest.gif' 
		img.save(fp=filename, format='GIF', append_images=imgs, save_all=True, duration=500, loop=0) #, quality=25, optimize=True, compress_level=9)
		print('inside saved', filename)
		compress_string = "magick mogrify -layers Optimize -fuzz 7% " + filename
		#subprocess.run(compress_string, shell=True)
		#optimize(filename)

caa = False # todo

if caa:
	auto = False
	windows = [1] # todo
	frames = 10
	enddate = datetime(2024,8,8) # todo	
	leftrow = 340
	rightrow = 690
	topcol = 1150
	bottomcol = 1500


if auto:
	today = datetime.today()
	today = datetime(today.year, today.month, today.day)
	enddate = today - timedelta(days = 1)

for window in windows:
	date = enddate	

	for k in range(frames):	
		startdate = date - timedelta(days = window-1)
		filename = getmedianfilename(startdate, date, caa)
		if not os.path.exists(filename):
			generateMedian(startdate, date, window, caa)
		date = date - timedelta(days = 1)
		
	if frames > 1:
		makeAnimation(enddate, window, caa)
if auto:
	time.sleep(10)
	filenames = ['animation_bremen_5_day_median_latest.gif', 'animation_bremen_3_day_median_latest.gif', 'animation_bremen_1_day_median_latest.gif']
	dropbox_client.uploadToDropbox(filenames)
