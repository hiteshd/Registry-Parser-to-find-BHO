#!/usr/bin/python

import sys,os,traceback
from datetime import date,timedelta
import os.path
import difflib
import glob
import re
import psycopg2


USAGE="%s days msie/chrome/firefox/all\nExample: %s 5 msie" % (sys.argv[0],sys.argv[0])

# Path giving location of logs
LOG_DIR='/data/farm/remote-rundata/on/'

""" Macros for logging """
ONLY_LOG="NO_EXTENSION_YET"
CHROME="chrome"
MSIE="msie"

""" Connect to Database """
conn_string = "host='129.174.117.10' dbname='browser' user='hitesh' password='dbpassword'"
 
conn = psycopg2.connect(conn_string)
 
cur = conn.cursor()
print "Connected to Database!\n"

# Creating a SQL in-case porting to another DB is required
fsql=open('sketchy.sql','w')

# Makes pair of md5 -> extension(chrome/msie)
def make_mapping(exec_id,chrome_id,msie_id):
    query="insert into mappings(exec_id,chrome_id,msie_id) values('%s','%s','%s')" % (exec_id,chrome_id,msie_id)
    cur.execute(query)
    fsql.write(query)
    fsql.write("\n")
    conn.commit()

# To prevent duplication and tighten the data
def check_id(table,primary_key,md5):
    status={'ret':0,'id':0}
    query=""
    if table==ONLY_LOG:
	query="select id from executions where md5='%s'" % md5
    elif (table==CHROME) or (table==MSIE):
	query="select id from %s where registry_key='%s' " % (table,primary_key['registry_key'])
    
    cur.execute(query)
    conn.commit()
    status['ret']=cur.fetchone()
    if status['ret']:
	status['id']=1
    else:
	status['id']=0
    return status


def addtodb(md5,LOG_TYPE,key_value):
    status=check_id(LOG_TYPE,key_value,md5)
    if status['id']:
	return status['ret'][0]
    query=""
    if LOG_TYPE==ONLY_LOG:
	query="insert into executions(md5) values('%s') returning id" % md5
    elif LOG_TYPE==CHROME:
	query="insert into chrome(registry_key,bho_name) values('%s','%s') returning id" % (key_value['registry_key'],key_value['bho_name'])
    elif LOG_TYPE==MSIE:
	query="insert into msie(registry_key,bho_name) values('%s','%s') returning id" % (key_value['registry_key'],key_value['bho_name'])

    fsql.write(query)
    fsql.write("\n")
    cur.execute(query)
    conn.commit()
    return cur.fetchone()[0]

# gets MD5 of all samples; used to fetch files later. all MD5s upto 'no_of_days' in the past are fetched
def get_all_md5(no_of_days):
    all_files=os.listdir(LOG_DIR)
    all_md5s=[]
    for f in all_files:
	if f.endswith('log') and ((date.fromtimestamp(int(f.split('.')[-2])))>date.today()-timedelta(days=int(no_of_days))):
	    all_md5s.append(f.split('.')[1])

    return sorted(set(all_md5s))
  
# Uses python diff library to get a diff and parse it - Feel free to modify based on what your diff will be
# Using re.sub , strip to sanitize input and split to get values of registry and BHO name from line

def parse_diff(log_type,diff,exec_id):
    msie_id=0
    chrome_id=0

    record={'registry_key':'','bho_name':''}
    lines=diff.splitlines()

    if log_type==CHROME:
	record['registry_key']=str(re.sub('[{}:;<>]','',lines[9].split("\\")[-1].strip()))
	record['bho_name']=str(re.sub('[{}:;<>]','',lines[12].split('"')[-2].strip()))
	chrome_id=addtodb(0,CHROME,record)

    elif log_type==MSIE:
	i=0   # Counter to keep us one line ahead - used to pickup values of extenions after a registry key is found in the diff
	for line in lines:
	    i+=1
	    if "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Browser Helper Objects\\{" in str(line) and (i < len(lines)):
		if "String" in str(lines[i]):
		    record['registry_key']=str(re.sub('[{}:;<> ]','',line.split("\\")[-1]))
		    record['bho_name']=str(re.sub('[^A-Za-z0-9]+','',lines[i].split(":")[-1]))
		elif "DWord" in str(lines[i]):
		    record['registry_key']=str(re.sub('[{}:;<> ]','',line.split("\\")[-1]))
                    record['bho_name']=str(re.sub('[^A-Za-z0-9]+','',lines[i+1].split(":")[-1])) 
		msie_id=addtodb(0,MSIE,record)		# Add newly found key to DB
		make_mapping(exec_id,chrome_id,msie_id) # Map the MD5 of sample and entry of registry key

def main():

    # Filtering out invalid command line arguments
    if (sys.argv[2] not in ['msie','chrome','firefox','all']):
		print "Invalid command line arguments. Try again\n"
		sys.exit(0)

    SAMPLE_AGE=sys.argv[1]

    all_md5s=get_all_md5(SAMPLE_AGE)

    # For debugging
    #all_md5s=[]
    #all_md5s.append('cc9c4807f73bbcf75f3ef3cd35fab2be')

    if sys.argv[2]=="all":
    	LOG_TYPES=[]
    	LOG_TYPES.append("msie")
    	LOG_TYPES.append("chrome")
    else:
	LOG_TYPES=[]
	LOG_TYPES.append(sys.argv[2])

    print "Found "+str(len(all_md5s))+" samples run in the last %s day(s)" % SAMPLE_AGE
    fp = open('diff_logs','w')


    for LOG_TYPE in LOG_TYPES:
    	print "Parsing %s logs\n" % LOG_TYPE
    	for one_md5 in all_md5s:
	    # Fetching pre_infection and post_browsing files for MD5 and Browser type
	    pre_infection=LOG_DIR+"*%s*%s*pre_infection*" % (one_md5,LOG_TYPE)
	    post_browsing=LOG_DIR+"*%s*%s*post_browsing*" % (one_md5,LOG_TYPE)

	    try:
		# with open takes care of closing file handles once complete
		with open(glob.glob(pre_infection)[0],'r') as pre_infection_handler:
		    with open(glob.glob(post_browsing)[0],'r') as post_browsing_handler:
		
			output=""
				    
			exec_id=addtodb(one_md5,ONLY_LOG,0)

			pre_infection_lines=pre_infection_handler.read().splitlines()
			post_browsing_lines=post_browsing_handler.read().splitlines()

			# Get unified diff - Needs to be made into list as unified_diff returns a generator class
			diff = list(difflib.unified_diff(pre_infection_lines, post_browsing_lines))
			output+='\n'.join(list(diff))
			
			# Parse diff
			parse_diff(LOG_TYPE,output,exec_id)

	    except Exception as e:
	        print "An error occoured while searching/processing for logs of %s. Skipping sample for analysis" % one_md5
		continue
    print "\nDone!"	
    #Cleaning up
    fp.close()
    fsql.close()

if __name__=="__main__":
    if len(sys.argv)<3:
	print USAGE
	sys.exit(0)
    print "Log location set to %s \n" % LOG_DIR
    main()
