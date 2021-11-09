from random import randint
import sys, traceback, threading, socket
from tkinter.constants import SEL

from VideoStream import VideoStream
from RtpPacket import RtpPacket
import time
class ServerWorker:
	SETUP = 'SETUP'
	PLAY = 'PLAY'
	PAUSE = 'PAUSE'
	TEARDOWN = 'TEARDOWN'
	DESCRIPTION = "DESCRIPTION"
	SKIP = 'SKIP'
	
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT


	OK_200 = 0
	FILE_NOT_FOUND_404 = 1
	CON_ERR_500 = 2
	
	clientInfo = {}
	
	def __init__(self, clientInfo):
		self.clientInfo = clientInfo
		self.wait_time=0.05
		self.frame_rate=20
	def run(self):
		threading.Thread(target=self.recvRtspRequest).start()
	
	def recvRtspRequest(self):
		"""Receive RTSP request from the client."""
		connSocket = self.clientInfo['rtspSocket'][0]
		while True:            
			data = connSocket.recv(256)#
			if data:
				print ("DATA RECEIVED: \n" + data.decode())
				self.processRtspRequest(data)
	
	def processRtspRequest(self, data):
		"""Process RTSP request sent from the client."""
		# Get the request type
		request = data.decode().split('\n')#['self.Type_STR self.fileName self.RTSP_VER',
		#									'CSeq: self.rtspSeq','Transport: self.TRANSPORT; client_port= self.rtpPort']
		line1 = request[0].split(' ')#self.Type_STR,self.fileName,self.RTSP_VER
		requestType = line1[0]

		# Get the media file name
		filename = line1[1]
		
		# Get the RTSP sequence number 
		seq = request[1].split(' ')
		
		# Process SETUP request
		if requestType == self.SKIP:
			if self.state != self.INIT:
				print ("PROCESSING SKIP")
				index_frame = int(request[3].split(' ')[1])
				self.clientInfo['videoStream'].set_frameNbr(index_frame-1)
				print('self.clientInfo.set_frameNbr_set',self.clientInfo['videoStream'].frameNbr())
				self.replyRtsp(self.OK_200, seq[1], self.totaltime)

		elif requestType == self.SETUP:
			if self.state == self.INIT:
				# Update state
				print ("PROCESSING SETUP\n")
				
				try:
					self.clientInfo['videoStream'] = VideoStream(filename)
					self.state = self.READY
				except IOError:
					self.replyRtsp(self.FILE_NOT_FOUND_404, seq[1])
				
				# Generate a randomized RTSP session ID
				self.clientInfo['session'] = randint(100000, 999999)
				self.totaltime=0.05*self.clientInfo['videoStream'].get_length()
				# Send RTSP reply
				self.replyRtsp(self.OK_200, seq[1],self.totaltime)
				# Get the RTP/UDP port from the last line
				self.clientInfo['rtpPort'] = request[2].split(' ')[3]#UDP

		# Process PLAY request 		
		elif requestType == self.PLAY:
			if self.state == self.READY:
				print ("PROCESSING PLAY\n")
				self.state = self.PLAYING
				
				# Create a new socket for RTP/UDP
				self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
				
				self.replyRtsp(self.OK_200, seq[1], self.totaltime)
				
				# Create a new thread and start sending RTP packets
				self.clientInfo['event'] = threading.Event()
				self.clientInfo['worker']= threading.Thread(target=self.sendRtp) 
				self.clientInfo['worker'].start()
		
		# Process PAUSE request
		elif requestType == self.PAUSE:
			if self.state == self.PLAYING:
				print ("PROCESSING PAUSE\n")
				self.state = self.READY
				self.clientInfo['event'].set()
				self.replyRtsp(self.OK_200, seq[1], self.totaltime)
		
		# Process TEARDOWN request
		elif requestType == self.TEARDOWN:
			print ("PROCESSING TEARDOWN\n")

			self.clientInfo['event'].set()
			
			self.replyRtsp(self.OK_200, seq[1])
			
			# Close the RTP socket
			self.clientInfo['rtpSocket'].close()

		# Process DESCRIPTION request
		elif requestType ==  self.DESCRIPTION and self.state != self.INIT:
			print("processing DESCRIPTION\n")

			self.sendDesc(self.OK_200, seq[1], self.totaltime)

	def sendDesc(self, code, seq, time = 0):
		if code == self.OK_200:
			reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + '\nSession: ' + str(self.clientInfo['session']) + '\ntotaltime: '+ str(time)
			packet = RtpPacket()
			packet.decode(self.RTPpacket)
			reply += '\nVersion: ' + str(packet.version())
			reply += '\nSequence number: ' + str(packet.seqNum())
			reply += '\nPayload type: ' + str(packet.payloadType())
			connSocket = self.clientInfo['rtspSocket'][0]
			connSocket.send(reply.encode())
		
		# Error messages
		elif code == self.FILE_NOT_FOUND_404:
			print("404 NOT FOUND")
		elif code == self.CON_ERR_500:
			print("500 CONNECTION ERROR")

	def sendRtp(self):
		"""Send RTP packets over UDP."""
		while True:
			self.clientInfo['event'].wait(0.05) 
			# Stop sending if request is PAUSE or TEARDOWN
			if self.clientInfo['event'].isSet(): 
				break 
			data = self.clientInfo['videoStream'].nextFrame()
			if data: 
				frameNumber = self.clientInfo['videoStream'].frameNbr()
				try:
					address = self.clientInfo['rtspSocket'][1][0]
					port = int(self.clientInfo['rtpPort'])
					self.RTPpacket = self.makeRtp(data, frameNumber)
					self.clientInfo['rtpSocket'].sendto(self.RTPpacket, (address,port))
				except:
					print ("Connection Error")
					#print '-'*60
					#traceback.print_exc(file=sys.stdout)
					#print '-'*60

	def makeRtp(self, payload, frameNbr):
		"""RTP-packetize the video data."""
		version = 2
		padding = 0
		extension = 0
		cc = 0
		marker = 0
		pt = 26 # MJPEG type
		seqnum = frameNbr
		ssrc = 0 
		
		rtpPacket = RtpPacket()
		
		rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)
		
		return rtpPacket.getPacket()
		
	def replyRtsp(self, code, seq, time=0):
		"""Send RTSP reply to the client."""
		if code == self.OK_200:
			#print "200 OK"
			reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + '\nSession: ' + str(self.clientInfo['session']) + '\ntotaltime: ' + str(time)
			connSocket = self.clientInfo['rtspSocket'][0]
			connSocket.send(reply.encode())
		
		# Error messages
		elif code == self.FILE_NOT_FOUND_404:
			print ("404 NOT FOUND")
		elif code == self.CON_ERR_500:
			print ("500 CONNECTION ERROR")
