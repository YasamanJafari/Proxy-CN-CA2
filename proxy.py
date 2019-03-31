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
	while not data:
		data = con.recv(DATA_SIZE).decode('UTF-8')
		print("$", data, "$$")
	if not data:
		print("NO DATA")
		return

	print("HELLLLO")
	host, request = convertProxyHTTPtoReqHTTP(data)
	print("HOST REQ")
	print(request)
	print(host)

	response = sendRequest(host, request)
	con.send(response)
	con.close()
	

def sendRequest(host, request):
	print("SEND REQUEST BEGIN")
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)                 
	
	print(host)
	s.connect((socket.gethostbyname(host), 80))
	s.sendall(request.encode())
	response = s.recv(4096)
	s.close()

	print(response)
	return response

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
		result.append(line + "\r\n")
	
	request = ""
	for line in result:
		request += line
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
	createSocket(parsedInfo["port"])
