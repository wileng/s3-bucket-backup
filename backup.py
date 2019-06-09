'''
	This program backs up files to buckets in AWS S3.
	
	Created by William Eng
'''


import boto3
import botocore
import os
import string
import time

i = 0
file_lastmod = {}

up_to_date = []
needs_update = []
id_bucket = []

cwd = os.getcwd()

#Prints the bucket contents, including file name and when it was last modified
def printBucketContents():
	for file, last_mod in file_lastmod.items():
		print(file, last_mod) 

#Prompts the user to select a bucket, or create a new one	
def promptBucketChoice():
	print("-------------------------------------------")
	print("Here are your current buckets:")
	for i in range(len(id_bucket)):
		print("[{}] '{}'".format(i, id_bucket[i]))
	print("-------------------------------------------")
	return raw_input("Print the bucket number you want to upload to, or type 'new' to create a new bucket\n")

#Gets user input regarding which bucket they would like to upload to
def getBucketChoice():
	user_input = promptBucketChoice()
	while True:
		try:
			user_input = int(user_input)
			if(user_input >= 0 and user_input < len(id_bucket)):
				return id_bucket[user_input]
		except ValueError:	
			if(isinstance(user_input, basestring) and user_input.lower() == 'new'):
				print("You want to create a new bucket!")
				name = createBucket()
				return name
		print("-------------------------------------------")
		print("Invalid input")
		user_input = promptBucketChoice()
		
#Creates a bucket based on user input
def createBucket():
	while True:
		name = str(raw_input("What would you like your bucket name to be?\n-------------------------------------------\n"))
		try:
			buck = s3.create_bucket(Bucket=name, CreateBucketConfiguration = {'LocationConstraint': 'us-west-2'})
			return name
		except Exception as e:
			if(e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou'):
				cont = True
				while cont:
					inp = str(raw_input("'{}' is already owned by you. Would you like to upload to this bucket? (y/n)\n".format(name)))
					if(inp == "y"):
						return name
					elif(inp == "n"):
						cont = false
					print("Invalid input")		
			print(str(e))

#Checks to see if the file exists in the bucket
def containsFile(file):
	if file in file_lastmod:
		#print("{} is already in here!".format(file))
		return True
	else:
		#print("{} is new".format(file))
		return False

#Builds an array of available buckets
def buildBucketIndex():
	for bucket in s3.buckets.all():
		id_bucket.append(bucket.name)

#Builds a dictionary from the bucket with file key to last_modified
def buildLastModDict(bucket_name):
	bucket = s3.Bucket(bucket_name)
	try:
		for key in bucket.objects.all():
			try:
				file_lastmod[key.key] = s3.Object(bucket_name, key.key).metadata["last_modified"]
			except KeyError:
				file_lastmod[key.key] = '0'
	except botocore.exceptions.ClientError as e:
		#print(str(e))
		if(e.response['Error']['Code'] == "AccessDenied"):
			print("Access denied to {}. Please check your user and bucket permissions.".format(bucket_name))
		exit()

#Builds the arrays of files that are up-to-date and files that need to be updated/uploaded
def update():
	for root, dirs, files in os.walk(cwd):
		for name in files:
			fullpath = os.path.join(root,name)
			key = fullpath.replace(cwd + "/", "")
			local_last_mod = str(os.stat(fullpath).st_mtime)
			#if the file is not in the bucket
			if not containsFile(key):
				needs_update.append((key, fullpath, local_last_mod))
			else:
				if(file_lastmod[key] != local_last_mod):
					#print("UPDATE REQUIRED")
					needs_update.append((key, fullpath, local_last_mod))
				else:
					up_to_date.append(key)
				#print("Bucket Last Mod: {}".format(file_lastmod[key]))
			#print("Local Last Mod: {}".format(local_last_mod))
			#print("-------------------------------------------")

#Prints the files that need to be updated
def printNeedsUpdate():
	print("The following files are new, or need to be updated")
	print("-------------------------------------------")
	for x in needs_update:
		print(x[0])
	print("-------------------------------------------\n")

#Prints the files that are up-to-date
def printUpToDate():
	print("The following files are up-to-date")
	print("-------------------------------------------")
	for x in up_to_date:
		print(x)
	print("-------------------------------------------\n")

#Updates files individually from the needs_update array
def update_indiv_from_list(buck):
	file_error = {}
	for x in needs_update[:]:
		proceed = True
		print(x[0])
		while proceed:
			inp = str(raw_input("Would you like to update '{}'? (y/n)\n".format(x[0])))
			if(inp == "y"):
				try:
					s3.Object(buck, x[0]).put(Body=open(x[1], "rb"), Metadata={'last_modified': str(x[2])})
					print("REMOVING: {}".format(x[0]))
					needs_update.remove(x)
					proceed = False
				except Exception as e:
					print("REMOVING: {}".format(x[0]))
					needs_update.remove(x)
					file_error[x[0]] = str(e)
					proceed = False
			elif(inp == "n"):
				print("REMOVING: {}".format(x[0]))
				needs_update.remove(x)
				proceed = False
			if(proceed):
				print("Invalid input")
			
	if(len(file_error) > 0):
		print("Error updating the following files:")
		for file, error in file_error:
			print(file)
			print("\t", error)
	else:
		print("Successfully updated all files!")
		
#Updates the ALL files from needs_update array
def update_all_from_list(buck):
	file_error = {}
	print("Updating all files...")
	for x in needs_update:
		try:
			s3.Object(buck, x[0]).put(Body=open(x[1], "rb"), Metadata = {'last_modified': str(x[2])})
		except Exception as e:
			file_error[x[0]] = str(e)
	if(len(file_error) > 0):
		print("Error updating the following files:")
		for file, error in file_error:
			print(file)
			print("\t", error)
	else:
		print("Successfully updated all files!")

#Prompts the user if they would like to see which files are up-to-date
def promptUpToDate():
	if(len(up_to_date) > 0):
		print("[{}] files are up-to-date".format(len(up_to_date)))
		while True:
			inp = str(raw_input("Would you like to see which are up-to-date? (y/n)"))
			if(inp == "y"):
				printUpToDate()	
				break
			elif(inp == "n"):
				break
			print("Invalid input")

#Prompts the user if they would like to see which files need to be updated/uploaded
def promptUpdate(buck):
	if(len(needs_update) > 0):
		while True:
			print("[{}] files need to be updated".format(len(needs_update)))
			while True:
				inp = str(raw_input("Would you like to see which files need to be updated? (y/n)"))
				if(inp == "y"):
					printNeedsUpdate()	
					break
				elif(inp == "n"):
					break
				print("Invalid input")
					
			inp = str(raw_input("Would you like to update these files invidiually or in bulk? Or cancel update? (indiv/bulk/cancel)\n"))
			if(inp == "bulk"):
				update_all_from_list(buck)
				break
			elif(inp == "indiv"):
				update_indiv_from_list(buck)
				break
			elif(inp == "cancel"):
				print("Not backing up these files. Exiting")
				exit()
			print("Invalid input")
	else:
		print("All files are up-to-date!")

#Tests connection to AWS S3, and tests credentials
def testConnection_Credentials():
	for i in range(3):
		time.sleep(i * 2)
		try:
			for bucket in s3.buckets.all():
				continue
			print("Successfully connected to s3!")
			return
		except (botocore.exceptions.EndpointConnectionError, botocore.exceptions.ClientError) as e:
			if(e.response['Error']['Code'] == 'SignatureDoesNotMatch'):
				print("Invalid keys. Double check your credentials.")
				exit()
			continue
	print("Could not connect to the server after 3 tries.\nPlease retry in a few minutes.".format(str(e)))
	exit()		

#Tests if the ~/.aws/credentials file is properly formatted
def testCredentials_Exist():
	try:
		temp = boto3.resource("s3")
		return temp
	except botocore.exceptions.ConfigParseError as e:
		print("Unable to parse your ~/.aws/credentials files. Double check this file")
		exit()
	

s3 = testCredentials_Exist()
testConnection_Credentials()
buildBucketIndex()
bucket_name = getBucketChoice()
buildLastModDict(bucket_name)
update()
promptUpToDate()
promptUpdate(bucket_name)


	
	

    

		
		

