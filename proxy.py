import datetime
import json
import socket
import threading
import signal

isLoggingNeeded = False
isPrivacyNeeded = False
defaultUserAgent = ""
logFileName = ""
portNum = ""
restrictedHosts = {}

HOST = '127.0.0.1'

CONFIG_FILE_NAME = "config.json"

PROXY_LAUNCH_MSG = "Proxy launched"
SOCKET_CREATION_MSG = "Creating server socket..."
BIND_PORT_MSG = "Binding socket to port "
LISTEN_FOR_REQ_MSG = "Listening for incoming requests..."
ACCEPT_REQ_FROM_CLIENT_MSG = "Accepted a request from client!"
CLIENT_REQ_MSG = "Client sent request to proxy with headers:"
BORDER = "\n----------------------------------------------------------------------\n"
LINE_DELIMETER = "\n"
SENDER_EMAIL = "sadaf.sadeghian@ut.ac.ir"
RECEIVER_EMAIL = "ys.jafari@ut.ac.ir"

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

def createSocket():
	writeMsgToFile(SOCKET_CREATION_MSG)
	threads = []
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		writeMsgToFile(BIND_PORT_MSG + str(portNum) + "...")
		s.bind((HOST, portNum))
		writeMsgToFile(LISTEN_FOR_REQ_MSG)
		s.listen(10)
		while True:
			con, addr = s.accept()
			thread = threading.Thread(target = processRequest, args = (con, addr, ))
			thread.setDaemon(True)
			thread.start()
			threads.append(thread)
	    
		s.close()

def processRequest(con, addr):
	writeMsgToFile(ACCEPT_REQ_FROM_CLIENT_MSG)
	data = ""
	isFirstPacket = True
	socket = ""
	with con:
		while True:
			data = con.recv(DATA_SIZE).decode("UTF-8")
			if len(data) <= 0:
				break
			if isFirstPacket:
				isFirstPacket = False
				
				isAccessRestricted = applyHostRestriction(data)
				if isAccessRestricted:
					break				
				
				host, request = convertProxyHTTPtoReqHTTP(data)
			
			socket = sendRequest(host, request, con)

	if data and (not isAccessRestricted):
		socket.close()
	con.close()

def applyHostRestriction(request):
	host = getHost(request)
	if host in restrictedHosts:
		if restrictedHosts.get(host):
			print("SENDING EMAIL")
			sendNotificationEmail(request)
		return True
	else:
		return False


def sendRequest(host, request, con):
	writeMsgToFile("connect to [" + str(host) + "] from " + HOST + " " + str(portNum))
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)                 
	
	s.connect((socket.gethostbyname(host), 80))
	s.sendall(request.encode())
	with con:
		while True:
			response = s.recv(DATA_SIZE)
			if len(response) > 0:
				con.send(response)
			else:
				return s

def getHost(request):
	host = ""
	header = getRequestHeader(request)
	lines = header.split("\r\n")
	for line in lines:
		if "Host: " in line:
			parts = line.split(" ")
			host = parts[1]
	return host

def getRequestHeader(request):
	parts = request.split("\r\n", 1)
	newParts = parts[1].split("\r\n\r\n", 1)
	header = newParts[0]
	return header + "\r\n"

def convertProxyHTTPtoReqHTTP(data):
	writeMsgToFile(CLIENT_REQ_MSG)
	writeMsgToFile(BORDER + getRequestHeader(data) + BORDER)
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
			if "Proxy-Connection: " in line:
				continue
			elif "Connection: " in line:
				line = "Connection: Close"
			if "User-Agent:" in line:
				if isPrivacyNeeded:
					line = "User-Agent: " + defaultUserAgent 
			if "Accept-Encoding: " in line:
				line = "Accept-Encoding: identify"
		result.append(line + "\r\n")
	
	request = ""
	for line in result:
		request += line
	return host, request
	
def processStartLine(startLine):
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

def sendNotificationEmail(data):
	emailSocket = socket.socket()
	emailSocket.connect((socket.gethostbyname("mail.ut.ac.ir"), 25))
	msg = emailSocket.recv(1024)
	print("CONNECTED", msg)
	emailSocket.send("HELO ut.ac.ir\r\n")
	msg = emailSocket.recv(1024)
	emailSocket.send("MAIL FROM: <" + SENDER_EMAIL + ">\r\n")
	msg = emailSocket.recv(10000)
	emailSocket.send("AUTH LOGIN\r\n")
	username = input("enter username: ").encode("base64")
	msg = emailSocket.recv(10000)
	emailSocket.send(username + "\r\n")
	msg = emailSocket.recv(1024)	
	password = input("enter password: ").encode("base64")
	emailSocket.send(password + "\r\n")
	msg = emailSocket.recv(10000)	
	emailSocket.send("RCPT TO: <" + RECEIVER_EMAIL + ">\r\n")	
	msg = emailSocket.recv(10000)	
	emailSocket.send("DATA")	
	msg = emailSocket.recv(10000)	
	emailSocket.send(data + "\r\n.\r\n")
	msg = emailSocket.recv(10000)	
	print("EMAIL SENT")
	emailSocket.send("QUIT\r\n")
	msg = emailSocket.recv(10000)	
	emailSocket.close()
	
		

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
	portNum = parsedInfo["port"]	

	if(parsedInfo["restriction"]["enable"]):
		for target in parsedInfo["restriction"]["targets"]:
			if target["notify"] == "true":
				restrictedHosts[target["URL"]] = True
			else:
				restrictedHosts[target["URL"]] = False
	createSocket()

