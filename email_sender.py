#!/usr/bin/env python3 

import os
import sys
import boto3
import time
import zmq
import json
import struct
import botocore.exceptions
import logging
from email import encoders
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os.path import basename


PROG = 'email sender'
CHARSET = "utf-8"


# Initialize logging
logger = logging.getLogger(PROG)
f = logging.Formatter('$name $message', style='$')
h = logging.StreamHandler(sys.stdout)
h.setFormatter(f)
logger.addHandler(h)

#Creating a class to load the ENV Variables
class EmailSenderConfigs:

    def __init__(self):
        self.aws_access_key_id = '#########################'
        self.aws_secret_access_key = '###########################################'
        self.region = "########"
        self.client_zmq_addr = '########################'

    def load_environ(self):
        #Read environment variables   
        aws_access_key_id = os.getenv("ENV_AWS_ACCESS_KEY_ID","").strip("")
        if aws_access_key_id:
            self.aws_access_key_id = aws_access_key_id

        aws_secret_access_key = os.getenv("ENV_AWS_SECRET_ACCESS_KEY","").strip("")
        if aws_secret_access_key:
            self.aws_secret_access_key = aws_secret_access_key

        client_zmq_addr = os.getenv("ENV_ZMQ_CLIENT_ADDR", "").strip("")
        if client_zmq_addr:
            self.client_zmq_addr = client_zmq_addr

        region = os.getenv("ENV_AWS_REGION", "").strip()
        if region:
            self.region = region



#Creating a class to send the Email using SES 
class EmailSender:

    def __init__(self,cfg_):
        self._access_key = cfg_.aws_access_key_id
        self._secret_key = cfg_.aws_secret_access_key
        self._zmq_addr = cfg_.client_zmq_addr
        self._region = cfg_.region
        self._socket = None
        self._context = None
        self._ses_client = None


    def _send(self,message_):

        message = message_
        from_addr = message[0].decode()
        to_addr = message[1].decode()
        subject = message[2].decode()
        body = message[3].decode()
        content_type = message[4].decode()
            
        #Sending the mail with attachments
        if len(message)==6:
            attachment_loc = message[5].decode()
            attachment_loc = json.loads(attachment_loc)
            logger.debug(f"Message of type {content_type} has an attachment")
            msg = None
            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = from_addr
            msg["To"] = to_addr
            body = body

            if content_type=="Text":
                body = MIMEText(f"{body}", "plain")

            elif content_type=="Html":
                body = MIMEText(f"{body}", "html")

            else:
                self._socket.send_string("Mail has failed to be sent")
                return

            msg.attach(body)
            attachment_loc = attachment_loc
            
            for file in attachment_loc:
                with open(file, "rb") as fil:
                    part = MIMEApplication(fil.read(),Name=basename(file))
                # After the file is closed
                part.add_header("Content-Disposition","attachment",filename="%s" % basename(file))
                msg.attach(part)
            response = self._ses_client.send_raw_email(Source=f"{from_addr}",
                                                Destinations=[f"{to_addr}"],
                                                RawMessage={"Data": msg.as_string()}
                                                )
            
        #Sending the mail without attachments
        else:
            response = self._ses_client.send_email(
                        Destination = {"ToAddresses": [f"{to_addr}",],},
                        Message = {"Body":{f"{content_type}": {"Charset": CHARSET,
                                    "Data": f"{body}", } },"Subject": {"Charset": CHARSET,"Data": f"{subject}",},},
                        Source=f"{from_addr}",
                        )

        self._socket.send_string("Mail has been sent")

        
    def stop(self):

        logger.info(f"Stopping {PROG} -----------------")
        if self._socket:
            self._socket.close()
            self._context.term()
         

    #Initializing the zmq_receiver    
    def start(self):
      
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REP)
        self._socket.bind(f"{self._zmq_addr}")
        self._ses_client = boto3.client("ses",
                                   aws_access_key_id=self._access_key,
                                   aws_secret_access_key=self._secret_key,
                                   region_name=self._region
                                  )

        logger.info(f"Server is listening on port {self._zmq_addr}")

        while True:

            try:
                message = self._socket.recv_multipart()
                if message:
                    if len(message)==5 or len(message)==6:
                        self._send(message)
                    else:
                        self._socket.send_string("Mail is invalid...")

            except Exception as e:
                logger.warning(str(e))
                self._socket.send_string("Mail has failed to be sent")





if __name__=='__main__':
    
    logger.info(f"Starting {PROG} -----------------")
    cfg = EmailSenderConfigs()
    cfg.load_environ()

    try:  #For Keyboard Interruption
        email = EmailSender(cfg)
        email.start()

    except Exception as e:
        logger.warning(str(e))

    except KeyboardInterrupt as k:
        logger.info(f"TERM signal received by {PROG} -----------------")

    finally:
        email.stop()

   
# End



 
 