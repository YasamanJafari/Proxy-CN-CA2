import json
import socket
import threading

HOST = "192.168.11.2"
CONFIG_FILE_NAME = "config.json"
DATA_SIZE = 1024

def createSocket(portNum):
	threads = []
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.bind(HOST, portNum)
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

# async def getRequesst():

if __name__ == "__main__":
	parsedInfo = readConfig()
	createSocket(parsedInfo["port"])
