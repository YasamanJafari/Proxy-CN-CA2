import datetime
import json
import socket
import threading
import signal
import base64

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

NEW_LINE_DELIM = "\r\n"

PROXY_LAUNCH_MSG = "Proxy launched"
SOCKET_CREATION_MSG = "Creating server socket..."
BIND_PORT_MSG = "Binding socket to port "
LISTEN_FOR_REQ_MSG = "Listening for incoming requests..."
ACCEPT_REQ_FROM_CLIENT_MSG = "Accepted a request from client!"
CLIENT_REQ_MSG = "Client sent request to proxy with headers:"
OPEN_CONNECTION_SERVER = "Proxy opening connection to server "
SERVER_CONNECTION_OPENED = "Connection opened."
PROXY_TO_SERVER_HEADER_MSG = "Proxy sent request to server with headers: "
PROXY_TO_CLIENT_HEADER_MSG = "Proxy sent response to client with headers: "
PROXY_TO_CLIENT_REQ_MSG = "Proxy sent request to client with headers: "
BORDER = "\n----------------------------------------------------------------------\n"
CACHED_DATA_USED = "Valid response was found in cache for request with header: "
RESPONSE_IS_CACHED_MSG = "Proxy cached the response for request with header: "
PROXY_CHANGED_USER_AGENT = "Proxy changed client's user-agent to add privacy."
PROXY_SENT_NOTIFICATION_MAIL = "Proxy found a restriction to notify the proxy manager: "
EMAIL_SENT_SUCCESSFULLY = "Notification mail successfully sent."
EMAIL_FAILURE = "Failed to send notification mail."
PROXY_ADDED_INJECTION_MSG = "Proxy injected a message in the index page."
REMANING_TRAFFIC_MSG = "Proxy reduced the volume for user and remaining traffic is "
LINE_DELIMETER = "\n"

MAIL_SERVER = "mail.ut.ac.ir"
HELO_EMAIL_MSG = "HELO ut.ac.ir\r\n"
MAIL_FROM_MSG = "MAIL FROM: <"
END_OF_EMAIL = ">\r\n"
AUTH_EMAIL_MSG = "AUTH LOGIN\r\n"
RCP_TO_MSG = "RCPT TO: <"
DATA_EMAIL_MSG = "DATA\r\n"
END_DATA_MSG = "\r\n.\r\n"
QUIT_EMAIL_MSG = "QUIT\r\n"
SENDER_EMAIL = "sadaf.sadeghian@ut.ac.ir"
RECEIVER_EMAIL = "ys.jafari@ut.ac.ir"

SENDER_USERNAME = "" #SET USERNAME
SENDER_PASS = ""	#SET PASSWORD

RESTRICTION_HTML = "<!DOCTYPE html><html><head>\n<meta charset=\"UTF-8\">\n</head><body style=\"background-color: #134444\"><h1 style=\"text-align: center; direction: rtl; color: white\">دسترسی به این سایت محدود شده است. </h1></body></html>"
ACCOUNTING_HTML = "<!DOCTYPE html><html><head>\n<meta charset=\"UTF-8\">\n</head><body style=\"background-color: #134444\"><h1 style=\"text-align: center; direction: rtl; color: white\">حجم قابل استفاده شما تمام شده است. </h1></body></html>"

IF_MOD_HEADER = "If-Modified-Since: "

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
	writeMsgToFile(REMANING_TRAFFIC_MSG + str(users[addrIP]) + " - " + str(amount) + " = " + str(users[addrIP] - amount) + " (for user with IP: " + addrIP + ")")
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
			writeMsgToFile("connect to [" + str(addr) + "] from " + HOST + " " + str(portNum))
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
			while not data:
				data = con.recv(DATA_SIZE)
			# decreaseVol(addr[0], len(data))
			if not isLegitimate(addr[0]):
				sendErrorToClient(con, getNotAllowedMsg())
				break

			data = data.decode("utf-8", "replace")
			
			if len(data) <= 0:
				break
			if isFirstPacket:
				isFirstPacket = False

				if applyHostRestriction(data, con):
					break				
				
				host, request, path = convertProxyHTTPtoReqHTTP(data)
			if canUseCachedResponse(request):
				writeMsgToFile(CACHED_DATA_USED + BORDER + getStartLine(request) + getRequestHeader(request) + BORDER)
				sendCachedResponse(request, con)
			else:			
				sendRequest(host, request, con, addr, path)
			break

		con.close()

def canUseCachedResponse(request):
	if request in cachedResponses:
		cachedData = cachedResponses.get(request)
		expiryDate = cachedData[0]
		if not (expiryDate == ""):
			return isValidate(expiryDate)
		else:
			return checkIfModified(request, expiryDate)
	else:
		return False

def checkIfModified(request, expiryDate):
	startLine = getStartLine(request)
	hostLine = ""
	header = getRequestHeader(request)
	lines = header.split(NEW_LINE_DELIM)
	for line in lines:
		if "Host:" in line:
			hostLine = line
	
	ifModReq = startLine + NEW_LINE_DELIM + hostLine + NEW_LINE_DELIM + IF_MOD_HEADER + expiryDate
	# print("IF-MOD REQ", ifModReq)

	#TODO:
	#create socket and send req
	



def isValidate(expiryDate):
	now = datetime.datetime.now()
	expire = datetime.datetime.strptime(expiryDate, '%a, %d %b %Y %H:%M:%S GMT')
	return(expire >= now)

def sendCachedResponse(request, con):
	with con:
		cachedData = cachedResponses.get(request)
		con.sendall(cachedData[1])

def applyHostRestriction(request, con):
	host = getHost(request)
	if host in restrictedHosts:
		sendErrorToClient(con, getForbiddenMsg())
		if restrictedHosts.get(host):
			writeMsgToFile(PROXY_SENT_NOTIFICATION_MAIL + RECEIVER_EMAIL + "(for host: " + str(host) + ")")
			sendNotificationEmail(request)
		return True
	else:
		return False

def getForbiddenMsg():
	header = "HTTP/1.1 403 Forbidden\nContent-Type: text/html\nConnection: close\nAccept-Ranges: bytes\nCache-Control: no-cache"
	msg = header + "\r\n\r\n" + RESTRICTION_HTML
	return msg

def getNotAllowedMsg():
	header = "HTTP/1.1 	406 Not Acceptable\nContent-Type: text/html\nConnection: close\nAccept-Ranges: bytes\nCache-Control: no-cache"
	msg = header + "\r\n\r\n" + ACCOUNTING_HTML
	return msg

def sendErrorToClient(con, msg):
	with con:
		con.send(msg.encode())

def sendRequest(host, request, con, addr, path):
	writeMsgToFile(OPEN_CONNECTION_SERVER + str(addr) + "...")
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)                 
	
	with con, s:
		cachingResponse = b""
		s.connect((socket.gethostbyname(host), 80))
		writeMsgToFile(SERVER_CONNECTION_OPENED + " (" + str(addr) + ")")
		s.sendall(request.encode())
		isFirstPacket = True
		while True:
			response = s.recv(DATA_SIZE)
			if len(response) > 0:
				if isFirstPacket:
					hasBody, header, body = getResponseParts(response)
					if isInjectionNeeded and path == "":
						if hasBody:
							info = header + "\r\n\r\n" + addNavBar(body)
							response = info.encode()

					writeMsgToFile(PROXY_TO_SERVER_HEADER_MSG + BORDER + header + BORDER)

				cachingResponse += response			
				con.send(response)
				if isFirstPacket:
					writeMsgToFile(PROXY_TO_CLIENT_HEADER_MSG + BORDER + header + BORDER)
				isFirstPacket = False
			else:
				decreaseVol(addr[0], len(cachingResponse))
				cachable, expiryDate = checkCacheData(cachingResponse)
				if cachable:
					cache(request, (expiryDate, cachingResponse))
				break
			response = ""
		s.close()

def checkCacheData(response):
	hasBody, header, body = getResponseParts(response)
	isCachable = True
	needValidation = False
	expiryDate = ""
	lines = header.split(NEW_LINE_DELIM)
	for line in lines:
		if "Cache-Control:" in line:
			if "no-store" in line:
				isCachable = False
			if "no-cache:" in line:
				needValidation = True
		elif "Pragma:" in line:
			if "no-cache" in line:
				isCachable = False
		elif "Expires:" in line:
			parts = line.split(" ", 1)
			expiryDate = parts[1]
	if needValidation:
		expiryDate = ""
	return isCachable, expiryDate

def cache(request, cachingResponse):
	writeMsgToFile(RESPONSE_IS_CACHED_MSG + BORDER + getStartLine(request) + getRequestHeader(request) + BORDER)
	cachedResponses[request] = cachingResponse

def getHost(request):
	host = ""
	header = getRequestHeader(request)
	lines = header.split(NEW_LINE_DELIM)
	for line in lines:
		if "Host: " in line:
			parts = line.split(" ")
			host = parts[1]
	return host

def getRequestHeader(request):
	parts = request.split(NEW_LINE_DELIM, 1)
	newParts = parts[1].split("\r\n\r\n", 1)
	header = newParts[0]
	return header + NEW_LINE_DELIM

def getStartLine(request):
	return (request.split(NEW_LINE_DELIM, 1))[0]

def getResponseParts(response):
	data = response.decode("utf-8", "ignore")
	parts = data.split("\r\n\r\n", 1) 
	if len(parts) > 1:
		return (True, parts[0], parts[1])
	return (False, parts[0], "")

def addNavBar(body):
	writeMsgToFile(PROXY_ADDED_INJECTION_MSG)
	addition = "<!DOCTYPE html>\n<html>\n<head>\n<meta charset=\"UTF-8\">\n</head>\n<body>\n<div style = \"background-color: #134444; color: white; direction: rtl; padding: 5px; padding-right: 10px; margin: 0px;\" />" + str(injectionMessage) + "\n</div>\n</body>\n</html>\n" 
	newBody = addition + body 
	return newBody

def convertProxyHTTPtoReqHTTP(data):
	writeMsgToFile(CLIENT_REQ_MSG + BORDER + getRequestHeader(data) + BORDER)
	lines = data.split(NEW_LINE_DELIM)
	
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
					writeMsgToFile(PROXY_CHANGED_USER_AGENT)
					line = "User-Agent: " + defaultUserAgent 
			if "Accept-Encoding: " in line:
				line = "Accept-Encoding: identify"
		result.append(line + NEW_LINE_DELIM)
	
	request = ""
	for line in result:
		request += line
	writeMsgToFile(PROXY_TO_CLIENT_REQ_MSG + BORDER + getRequestHeader(request) + BORDER)
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
	
	result = reqType + " /" + path + " HTTP/1.0" + NEW_LINE_DELIM
	return host, result, path

def setLegitimateUsers(usersInfo):
	for item in usersInfo:
		userIP = item["IP"]
		userVolume = item["volume"]
		users[userIP] = int(userVolume)

def getBase64(data):
	return base64.b64encode(data.encode()).decode() 

def sendNotificationEmail(data):
	emailSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	emailSocket.connect((MAIL_SERVER, 25))
	emailSocket.recv(1024)
	emailSocket.send((HELO_EMAIL_MSG).encode())
	emailSocket.recv(1024)
	emailSocket.send((MAIL_FROM_MSG + SENDER_EMAIL + END_OF_EMAIL).encode())
	emailSocket.recv(10000)
	emailSocket.send((AUTH_EMAIL_MSG).encode())
	username = getBase64(SENDER_USERNAME) 
	emailSocket.recv(10000)
	emailSocket.send((username + NEW_LINE_DELIM).encode())
	emailSocket.recv(1024)	
	password = getBase64(SENDER_PASS) 
	emailSocket.send((password + NEW_LINE_DELIM).encode())
	msg = emailSocket.recv(10000).decode()
	if "authentication failed" in msg:
		writeMsgToFile(EMAIL_FAILURE)
		emailSocket.close()	
		return
	emailSocket.send((RCP_TO_MSG + RECEIVER_EMAIL + END_OF_EMAIL).encode())	
	emailSocket.recv(10000)	
	emailSocket.send((DATA_EMAIL_MSG).encode())	
	emailSocket.recv(10000)	
	emailSocket.send((data + END_DATA_MSG).encode())
	emailSocket.recv(10000)	
	writeMsgToFile(EMAIL_SENT_SUCCESSFULLY)
	emailSocket.send((QUIT_EMAIL_MSG).encode())
	emailSocket.recv(10000)	
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
	setLegitimateUsers(parsedInfo["accounting"]["users"])
	createSocket()

