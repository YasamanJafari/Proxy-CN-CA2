import datetime
import json
import socket
import threading
import signal

isLoggingNeeded = False
isPrivacyNeeded = False
isInjectionNeeded = False
injectionMessage = ""
defaultUserAgent = ""
logFileName = ""
portNum = ""
restrictedHosts = {}
users = {}
cachedResponses = {}

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

def isLegitimate(addrIP):
	if addrIP in users:
		if users[addrIP] > 0:
			return True
	return False

def decreaseVol(addrIP, amount):
	users[addrIP] = users[addrIP] - amount

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
	with con:
		while True:
			data = con.recv(DATA_SIZE)
			decreaseVol(addr[0], len(data))
			if not isLegitimate(addr[0]):
				break

			data = data.decode("utf-8", "replace")
			
			# if applyHostRestriction(data):
			# 		break
			
			if len(data) <= 0:
				break
			if isFirstPacket:
				isFirstPacket = False
				
				# if applyHostRestriction(data):
				# 	break				
				
				host, request, path = convertProxyHTTPtoReqHTTP(data)
			if canUseCachedResponse(request):
				sendCachedResponse(request, con)
			else:			
				sendRequest(host, request, con, addr, path)

		con.close()

def canUseCachedResponse(request):
	if request in cachedResponses:
		# if isValidation(request):
		return True
	else:
		return False

def sendCachedResponse(request, con):
	print("USING CACHED DATA")
	with con:
		cachedData = cachedResponses.get(request)
		con.sendall(cachedData[1])

def applyHostRestriction(request):
	host = getHost(request)
	if host in restrictedHosts:
		if restrictedHosts.get(host):
			print("SENDING EMAIL")
		# 	sendNotificationEmail(request)
		return True
	else:
		return False

def sendRequest(host, request, con, addr, path):
	writeMsgToFile("connect to [" + str(host) + "] from " + HOST + " " + str(portNum))
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)                 
	
	with con, s:
		cachingResponse = b""
		s.connect((socket.gethostbyname(host), 80))
		s.sendall(request.encode())
		while True:
			response = s.recv(DATA_SIZE)
			if len(response) > 0:
				if isInjectionNeeded and path == "":
					hasBody, header, body = getResponseParts(response)
					if hasBody:
						info = header + "\r\n\r\n" + addNavBar(body)
						response = info.encode()
				
				decreaseVol(addr[0], len(response))	

				cachingResponse += response			
				con.send(response)
			else:
				cachable, expireDate = checkCachData(response)
				if cachable:
					cache(request, (expireDate, cachingResponse))
				break
		s.close()

def checkCachData(response):
	hasBody, header, body = getResponseParts(response)
	isCachable = True
	expireDate = None
	lines = header.split("\r\n")
	for line in lines:
		if "Cache-Control:" in line:
			if "no-cache" in line:
				isCachable = False
		elif "Pragma:" in line:
			if "no-cache" in line:
				isCachable = False
		elif "expires:" in line:
			parts = line.split(" ")
			expireDate = parts[1]
	return isCachable, expireDate

def cache(request, cachingResponse):
	cachedResponses[request] = cachingResponse
			

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

def getResponseParts(response):
	data = response.decode("utf-8", "ignore")
	parts = data.split("\r\n\r\n", 1) 
	if len(parts) > 1:
		return (True, parts[0], parts[1])
	return (False, parts[0], "")

def addNavBar(body):
	if "<body" in body:
		print("DAMN")
		addition = "<!DOCTYPE html>\n<html>\n<head>\n<meta charset=\"UTF-8\">\n</head>\n<body>\n<div style = \"background-color: #134444; color: white; direction: rtl; padding: 5px; padding-right: 10px; margin: 0px;\" />" + str(injectionMessage) + "\n</div>\n</body>\n</html>\n" 
		newBody = addition + body 
		return newBody
	return body

def convertProxyHTTPtoReqHTTP(data):
	writeMsgToFile(CLIENT_REQ_MSG)
	writeMsgToFile(BORDER + getRequestHeader(data) + BORDER)
	lines = data.split("\r\n")
	
	startLine = lines[0]
	host, startLine, path = processStartLine(startLine)
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
	return host, request, path
	
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
	return host, result, path

def getLegitimateUsers(usersInfo):
	for item in usersInfo:
		userIP = item["IP"]
		userVolume = item["volume"]
		users[userIP] = int(userVolume)

def sendNotificationEmail(data):
	emailSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	emailSocket.connect(("mail.ut.ac.ir", 25))
	msg = emailSocket.recv(1024)
	emailSocket.send(("HELO ut.ac.ir\r\n").encode())
	msg = emailSocket.recv(1024)
	emailSocket.send(("MAIL FROM: <" + SENDER_EMAIL + ">\r\n").encode())
	msg = emailSocket.recv(10000)
	emailSocket.send(("AUTH LOGIN\r\n").encode())
	username = "" #SET USERNAME
	msg = emailSocket.recv(10000)
	emailSocket.send((username + "\r\n").encode())
	msg = emailSocket.recv(1024)	
	password = "" #SET USERNAME
	emailSocket.send((password + "\r\n").encode())
	msg = emailSocket.recv(10000)	
	emailSocket.send(("RCPT TO: <" + RECEIVER_EMAIL + ">\r\n").encode())	
	msg = emailSocket.recv(10000)	
	emailSocket.send(("DATA\r\n").encode())	
	msg = emailSocket.recv(10000)	
	emailSocket.send((data + "\r\n.\r\n").encode())
	msg = emailSocket.recv(10000)	
	print("EMAIL... ", msg)
	print("EMAIL SENT")
	emailSocket.send(("QUIT\r\n").encode())
	msg = emailSocket.recv(10000)	
	emailSocket.close()
	
def readConfig():
	with open(CONFIG_FILE_NAME) as json_file:  
		data = json.load(json_file)
	return data

if __name__ == "__main__":
	writeMsgToFile(PROXY_LAUNCH_MSG)
	parsedInfo = readConfig()
	isPrivacyNeeded = parsedInfo["privacy"]["enable"]
	isLoggingNeeded = parsedInfo["logging"]["enable"]
	isInjectionNeeded = parsedInfo["HTTPInjection"]["enable"]
	injectionMessage = parsedInfo["HTTPInjection"]["post"]["body"]
	portNum = parsedInfo["port"]
	if(isLoggingNeeded):
		logFileName = parsedInfo["logging"]["logFile"]
	if(isPrivacyNeeded):
		defaultUserAgent = parsedInfo["privacy"]["userAgent"]	
	if(parsedInfo["restriction"]["enable"]):
		for target in parsedInfo["restriction"]["targets"]:
			if target["notify"] == "true":
				restrictedHosts[target["URL"]] = True
			else:
				restrictedHosts[target["URL"]] = False
	getLegitimateUsers(parsedInfo["accounting"]["users"])
	createSocket()

