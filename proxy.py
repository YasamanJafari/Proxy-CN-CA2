import datetime
import json
import socket
import threading

isLoggingNeeded = False
isPrivacyNeeded = False
defaultUserAgent = ""
logFileName = ""

HOST = '127.0.0.1'

CONFIG_FILE_NAME = "config.json"

PROXY_LAUNCH_MSG = "Proxy launched"
SOCKET_CREATION_MSG = "Creating server socket..."
BIND_PORT_MSG = "Binding socket to port "
LISTEN_FOR_REQ_MSG = "Listening for incoming requests..."
ACCEPT_REQ_FROM_CLIENT = "Accepted a request from client!"
LINE_DELIMETER = "\n"

DATA_SIZE = 8192

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
		s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
	isFirstPacket = True
	socket = ""
	while True:
		data = con.recv(DATA_SIZE).decode("UTF-8")
		if not data:
			break
		if isFirstPacket:
			isFirstPacket = False
			host, request = convertProxyHTTPtoReqHTTP(data)
		
		socket = sendRequest(host, request, con)

	# if data:
	# 	socket.close()
	# con.close()

def sendRequest(host, request, con):
	print("SEND REQUEST BEGIN")
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)                 
	
	print(host)
	s.connect((socket.gethostbyname(host), 80))
	s.sendall(request.encode())
	while True:
		response = s.recv(DATA_SIZE)
		con.send(response)
		if not response:
			return s

def getRequestHeader(request):
	parts = request.split("\r\n", 1)
	
	newParts = parts[1].split("\r\n\r\n", 1)

	header = newParts[0]
	
	return header + "\r\n"

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
			if "User-Agent:" in line:
				line = "User-Agent: " + defaultUserAgent 
		result.append(line + "\r\n")
	
	request = ""
	for line in result:
		request += line
	print(request)
	return host, request
	
def processStartLine(startLine):
	print("STARTLINE", startLine)
	parts= startLine.split(" ")
	reqType = parts[0]
	
	url = parts[1]
	host = ""
	path = ""
	if url.count("//") == 1:
		urlParts = url.split("/", 3)
		path = urlParts[3]
		host = urlParts[2]
	
	elif url.count("/") > 0:
		urlParts = url.split("/", 1)
		path = urlParts[1]
		host = urlParts[0]
	
	else:
		host = url
		path = ""
	
	result = reqType + " /" + path + " HTTP/1.0" + "\r\n"
	return host, result

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
	isPrivacyNeeded = parsedInfo["privacy"]["enable"]
	if(isPrivacyNeeded):
		defaultUserAgent = parsedInfo["privacy"]["userAgent"]	
	createSocket(parsedInfo["port"])
