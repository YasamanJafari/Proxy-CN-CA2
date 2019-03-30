import asyncio
import json
import socket

HOST = "192.168.11.2"
CONFIG_FILE_NAME = "config.json"

def createSocket(portNum):
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
	    s.bind((HOST, portNum))
	    s.listen()
	    con, addr = s.accept()
	    return con, addr

def readConfig():
	with open(CONFIG_FILE_NAME) as json_file:  
		data = json.load(json_file)
	return data

if __name__ == "__main__":
	parsedInfo = readConfig()
	createSocket(parsedInfo["port"])
