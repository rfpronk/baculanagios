#!/usr/bin/python
#
# Bacula job check for Nagios
# https://github.com/rfpronk/baculanagios
#

import sys
import mysql.connector

cnx = mysql.connector.connect(user='nagiosscript', password='DBPASSWORD', database='bacula') # used for database connection
cursor = cnx.cursor()

# fetches information from the database

Jobs = ("SELECT Name, ANY_VALUE(ClientId), ANY_VALUE(Level), SUM(JobErrors), SUM(JobBytes), ANY_VALUE(JobStatus) AS JobStatus, ANY_VALUE(StartTime) AS StartTime, ANY_VALUE(JobId), ANY_VALUE(JobFiles) FROM Job where JobStatus IN ('T', 'E', 'e', 'f') AND StartTime between NOW() - INTERVAL 1 DAY AND NOW() GROUP BY Name ORDER BY StartTime DESC LIMIT 100;")
Clients = ("SELECT Name, ClientId, Active FROM Client WHERE Active = 1;")
# average size full backup:
Avsizef = ("SELECT ClientId, ANY_VALUE(Name), AVG(JobBytes), ANY_VALUE(Level), ANY_VALUE(JobId), ANY_VALUE(StartTime) AS StartTime FROM Job where Level = 'F' AND StartTime BETWEEN NOW() - INTERVAL 40 DAY AND NOW() - INTERVAL 1 DAY GROUP BY ClientID;")
# average size incremental backup:
Avsizei = ("SELECT ClientId, ANY_VALUE(Name), AVG(JobFiles), ANY_VALUE(Level), ANY_VALUE(JobId), ANY_VALUE(StartTime) AS StartTime FROM Job where Level = 'I' AND StartTime BETWEEN NOW() - INTERVAL 14 DAY AND NOW() - INTERVAL 1 DAY GROUP BY ClientID;")

cursor.execute(Jobs)
Joblist = cursor.fetchall()
cursor.execute(Clients)
Clientlist = cursor.fetchall()
cursor.execute(Avsizef)
Avsizelistf = cursor.fetchall()
cursor.execute(Avsizei)
Avsizelisti = cursor.fetchall()

exitcode = 0			#	set exitcode to 0
clientjobfiles = {}		#	used to map the number of files in the job with the client ID
jobclientname = []		#	array with clientnames from the joblist
jobclientid = []		#	array with jobclientid
activeclientid = {}		#	used to map the active clients with the clientid
clientnumerrors = {}		#	used to map the number of errors to the clientid
clientjobstatus = {}		#	used to map the job status to the clientid
clientbackuptype = {}		#	used to map the backup type to the clientid
clientjobbytes = {}		#	used to map the job bytes to the clientid
okclient = []			#	array with clients that are ok
warningclient = []		#	array with clients with warnings
errorclient = []		#	array with clients with errors
nojobclient = []		#	array with clients without jobs
JobFilesASD = {}		#	maps the average number of jobfiles to the clientid
JobFilesOK = []			#	array with clients that passed the jobfile test
JobFilesErr = []		#	array with clients that failed the jobfile test
JobBytesOK = []			#	array with clients that passed the jobbyte test
JobBytesErr = []		#	array with clients that failed the jobbyte test
JobBytesASD = {}		#	maps the average jobbytes to the client ID

cursor.close()
cnx.close()

for row in Clientlist:
	clientnameCL = row[0]
	clientidCL = row[1]
	active = row[2]

	activeclientid[clientidCL] = clientnameCL # maps clientname to clientid

for row in Joblist:
	clientnameJL = row[0]
	print(row[0])
	clientidJL = row[1]
	backuptype = row[2]
	numerrors = row[3]
	JobBytes = row[4]
	JobStatus = row[5]
	JobFiles = row[8]
	jobclientname.append(clientnameJL)
	jobclientid.append(clientidJL)
	clientnumerrors[clientidJL] = numerrors # maps number of errors to clientid
	clientjobstatus[clientidJL] = JobStatus # maps job status to clientid
	clientbackuptype[clientidJL] = backuptype # maps backup type to clientid
	clientjobbytes[clientidJL] = JobBytes # maps amount of bytes to clientid
	clientjobfiles[clientidJL] = JobFiles # maps amount of files to clientid

for row in Avsizelisti:
	clientidASi = row[0]
	JobFilesAS = int(row[2])
	JobFilesASD[clientidASi] = JobFilesAS # maps average amount of job files to clientid

for clientidASi in JobFilesASD:
	MinJobFilesAS = (JobFilesASD[clientidASi]*0.7) # used to decide on the minimum amount of job files, based on the average size
	MaxJobFilesAS = (JobFilesASD[clientidASi]*1.3) # used to decide on the maximum amount of job files, based on the average size
	if MinJobFilesAS < JobFilesASD[clientidASi] < MaxJobFilesAS: # checks if the amount of job files is between the minimum and maximum values. If so, the clientid is appended to JobFilesOK
		JobFilesOK.append(clientidASi)
	else:
		JobFilesErr.append(clientidASi) # else, it is appended to JobFilesErr

for row in Avsizelistf:
        clientidASf = row[0]
        JobBytesAS = int(row[2])
	JobBytesASD[clientidASf] = JobBytesAS # maps average amount of job bytes to clientid 

for clientidASf in JobBytesASD:
	MinJobBytesAS = (JobBytesASD[clientidASf]*0.7) # used to decide on the minimum amount of job bytes, based on the average size
	MaxJobBytesAS = (JobBytesASD[clientidASf]*1.3) # used to decide on the maximum amount of job bytes, based on the average size
	if MinJobBytesAS < JobBytesASD[clientidASf] < MaxJobBytesAS: # checks if the amount of job bytes is between the minimum and maximum values. If so, the clientid is appended to JobBytesOK
		JobBytesOK.append(clientidASf)
	else:
		JobBytesErr.append(clientidASf) # else, it is appended to JobBytesErr

for clientidCL in activeclientid: # for every client in the active client list:
	if (clientidCL in jobclientid): # if the clientid is in the jobclientid array:
		if clientbackuptype[clientidCL] == 'F': # if the backuptype = F (full):
			if (clientnumerrors[clientidCL] == 0 and clientjobbytes[clientidCL] != 0 and clientjobstatus[clientidCL] == 'T' and clientidCL in JobBytesOK): # if all conditions are met:
				okclient.append(clientidCL)	# clientid is added to okclient
			elif (clientnumerrors[clientidCL] != 0) or (clientjobbytes[clientidCL] == 0) or (clientjobstatus[clientidCL] == 'e') or (clientidCL in JobBytesErr): # if one of the conditions fails:
				warningclient.append(clientidCL) # clientid is added to warningclient
				if exitcode < 1:
					exitcode = 1; # exitcode is 1
			elif (clientjobstatus[clientidCL] == 'E' or clientjobstatus[clientidCL] == 'f'):
				errorclient.append(clientidCL) # client is added to errorclient
				if exitcode <= 1:
					exitcode = 2; # exitcode is 2
		elif clientbackuptype[clientidCL] == 'I': # if the backuptype = I (incremental:)
			if (clientnumerrors[clientidCL] == 0 and clientjobbytes[clientidCL] != -1 and clientjobstatus[clientidCL] == 'T' and (clientidCL in JobFilesOK)): # if all conditions are met:
				okclient.append(clientidCL)	# clientid is added to okclient
			elif (clientnumerrors[clientidCL] != 0) or (clientjobbytes[clientidCL] == 0) or (clientjobstatus[clientidCL] == 'e') or (clientidCL in JobFilesErr): # if one of the conditions fails:
				warningclient.append(clientidCL) # clientid is added to warningclient
				if exitcode < 1:
					exitcode = 1; # exitcode is 1
			elif (clientjobstatus[clientidCL] == 'E' or clientjobstatus[clientidCL] == 'f'):
				errorclient.append(clientidCL) # client is added to errorclient
				if exitcode <= 1:
					exitcode = 2; # exitcode is 2

	else: # in this case, the job is not in the active client list
		nojobclient.append(clientidCL) # add clientid to nojobclient
		exitcode = 2; # exitcode is 2

#checks if the clientid is in nojobclient, errorclient, warningclient or okclient and prints information

print("-- Critical --");
for clientidCL in nojobclient:
	print(" Client: {:40} not in joblist".format(activeclientid[clientidCL]))
for clientidCL in errorclient:
	print(" Client: {:40} Backuptype: {:5} Errors: {:<10} Status: {:10} JobBytes: {:<15} CRITICAL".format(activeclientid[clientidCL], clientbackuptype[clientidCL], clientnumerrors[clientidCL], clientjobstatus[clientidCL], clientjobbytes[clientidCL]))
print("-- Warning --");
for clientidCL in warningclient:
	print(" Client: {:40} Backuptype: {:5} Errors: {:<10} Status: {:10} JobBytes: {:<15} WARNING".format(activeclientid[clientidCL], clientbackuptype[clientidCL], clientnumerrors[clientidCL], clientjobstatus[clientidCL], clientjobbytes[clientidCL]))
print("-- Ok --");
for clientidCL in okclient:
	print(" Client: {:40} Backuptype: {:5} Errors: {:<10} Status: {:10} JobBytes: {:<15}".format(activeclientid[clientidCL], clientbackuptype[clientidCL], clientnumerrors[clientidCL], clientjobstatus[clientidCL], clientjobbytes[clientidCL]))

sys.exit(exitcode) # passes the exitcode to the system
