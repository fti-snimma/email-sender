import zmq
import json
import struct
import time
context = zmq.Context()

#Socket to talk to server
print("Connecting to the zmq server…")
socket = context.socket(zmq.REQ)
socket.connect('tcp://127.0.0.1:2000')

# Do requests, waiting each time for a response
for request in range(1):
	time.sleep(2)
	from_addr = "##########@#######"
	to_addr = "#############@########"
	subject = "" 
	body = ""   #"<html><body>This is a text body to send SES...<strong>HELLOO!!</strong></body></html>"
	content_type = ""  #Html or Text
	attachment_location = ["#####","######"]
	attachment_location = json.dumps(attachment_location)
	buff = [from_addr.encode("utf-8"),to_addr.encode("utf-8"),subject.encode("utf-8"),body.encode("utf-8"),content_type.encode("utf-8"),attachment_location.encode("utf-8")]
	socket.send_multipart(buff)
	msg = socket.recv()
	print(msg)
