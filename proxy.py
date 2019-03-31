import datetime
import json
import socket
import threading

isLoggingNeeded = False
logFileName = ""

HOST = '127.0.0.1'

CONFIG_FILE_NAME = "config.json"

PROXY_LAUNCH_MSG = "Proxy launched"
SOCKET_CREATION_MSG = "Creating server socket..."
BIND_PORT_MSG = "Binding socket to port "
LISTEN_FOR_REQ_MSG = "Listening for incoming requests..."
ACCEPT_REQ_FROM_CLIENT = "Accepted a request from client!"
LINE_DELIMETER = "\n"

DATA_SIZE = 1024

def getCurrentTime():
	now = datetime.datetime.now()
	parsedTime = now.strftime("[%d/%b/%Y:%H:%M:%S] ")
	return parsedTime

def writeMsgToFile(message):
	if(not isLoggingNeeded):
		return
	now = getCurrentTime()
	logFile = open(logFileName, "a")
	logFile.write(now)
	logFile.write(message + LINE_DELIMETER)
	logFile.close()

def createSocket(portNum):
	writeMsgToFile(SOCKET_CREATION_MSG)
	threads = []
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		writeMsgToFile(BIND_PORT_MSG + str(portNum) + "...")
		s.bind((HOST, portNum))
		writeMsgToFile(LISTEN_FOR_REQ_MSG)
		s.listen()
		while True:
			con, addr = s.accept()
			thread = threading.Thread(target = processRequest, args = (con, addr, ))
			thread.start()
			threads.append(thread)
	    
		for thread in threads:
			thread.join()

def processRequest(con, addr):
	writeMsgToFile(ACCEPT_REQ_FROM_CLIENT)
	data = ""
	while True:
		data += con.recv(DATA_SIZE)
		if not data:
			break
	host, request = convertProxyHTTPtoReqHTTP(data)
	
	#TODO:
	#send request to server
	#recv response from server
	#send response to client

def convertProxyHTTPtoReqHTTP(data):
	lines = data.split("\r\n")
	
	startLine = lines[0]
	host, startLine = processStartLine(startLine)
	result = [startLine]

	lines = lines[1:]
	header = True
	for line in lines:
		if line == "":
			header = False
		if header:
			if "Proxy-Connection:" in line:
				continue
		result.append(line)
	return host, result
	
def processStartLine(startLine):
	parts = startLine.split("//")
	url, http = parts[1].split(" ")
	
	urlParts = url.split("/", 1)
	url = "/" + urlParts[1]
	
	result = parts[0] + url + " HTTP/1.0"
	return urlParts[0], result

def readConfig():
	with open(CONFIG_FILE_NAME) as json_file:  
		data = json.load(json_file)
	return data

if __name__ == "__main__":
	writeMsgToFile(PROXY_LAUNCH_MSG)
	parsedInfo = readConfig()
	isLoggingNeeded = parsedInfo["logging"]["enable"]
	if(isLoggingNeeded):
		logFileName = parsedInfo["logging"]["logFile"]
	createSocket(parsedInfo["port"])
