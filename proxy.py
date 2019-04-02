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
users = {}

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
EMAIL_DATA = "Hi :) It's a test."

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
			print("*** " + str(addr) + " ***")
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
			if len(data) <= 0:
				break
			if isFirstPacket:
				isFirstPacket = False
				host, request = convertProxyHTTPtoReqHTTP(data)
				sendRequest(host, request, con, addr)
		con.close

def sendRequest(host, request, con, addr):
	writeMsgToFile("connect to [" + str(host) + "] from " + HOST + " " + str(portNum))
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)                 
	
	with con, s:
		s.connect((socket.gethostbyname(host), 80))
		s.sendall(request.encode())
		while True:
			response = s.recv(DATA_SIZE)
			if len(response) > 0:
				decreaseVol(addr[0], len(response))
				con.send(response)
			else:
				break
		s.close()

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

def getLegitimateUsers(usersInfo):
	for item in usersInfo:
		userIP = item["IP"]
		userVolume = item["volume"]
		users[userIP] = int(userVolume)

def sendEmail():
	emailSocket = socket.socket()
	emailSocket.connect(("mail.ut.ac.ir", 25))
	msg = emailSocket.recv(1024)
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
	emailSocket.send(EMAIL_DATA + "\r\n.\r\n")
	msg = emailSocket.recv(10000)	
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
	getLegitimateUsers(parsedInfo["accounting"]["users"])
	createSocket()
