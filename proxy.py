import datetime
import json
import socket
import threading

HOST = '127.0.0.1'
CONFIG_FILE_NAME = "config.json"
LOG_FILE_NAME = "proxy.log"
DATA_SIZE = 1024

def writeLogInFile():
	logFile = open(LOG_FILE_NAME, "a")
	now = getCurrentTime()
	logFile.write(now.strftime("[%d/%b/%Y:%H:%M:%S]"), end =" ")
	logFile.close()

def getCurrentTime():
	return datetime.datetime.now()	

def createSocket(portNum):
	threads = []
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.bind((HOST, portNum))
		s.listen()
		while True:
			con, addr = s.accept()
			thread = threading.Thread(target = processRequest, args = (con, addr, ))
			thread.start()
			threads.append(thread)
	    
		for thread in threads:
			thread.join()

def processRequest(con, addr):
	data = ""
	while True:
		data += con.recv(DATA_SIZE)
		if not data:
			break
	# parsedData = parseHTTP(data)
	#TODO: 
	#send request to server
	#recv response from server
	#send response to client

#def parseHTTP(data):


def readConfig():
	with open(CONFIG_FILE_NAME) as json_file:  
		data = json.load(json_file)
	return data

# async def getRequest():

if __name__ == "__main__":
	parsedInfo = readConfig()
	createSocket(parsedInfo["port"])
