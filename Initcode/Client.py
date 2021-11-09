from tkinter import *
import tkinter.messagebox
from tkinter import ttk
tkinter.messagebox
from tkinter import messagebox 
tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os
from time import time
import datetime
from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
	SWITCH = -1
	INIT = 0
	READY = 1
	PLAYING = 2
	state = SWITCH
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3
	SKIP = 4
	DESCRIPTION = 5

	RTSP_VER = "RTSP/1.0"
	TRANSPORT = "RTP/UDP"
	
	
	SETUP_STR = 'SETUP'
	PLAY_STR = 'PLAY'
	PAUSE_STR = 'PAUSE'
	TEARDOWN_STR = 'TEARDOWN'
	SKIP_STR= 'SKIP'
	
	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)

		self.breakpoint = 0
		self.listfilm = filename
		self.index = -1
		self.played = 0
		self.removed = 0
		self.paused = 0

		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		self.index_frame=0

	def delayfunc(self, x):
		start = time()
		while True:
			end = time()
			if float(end - start) > float(x):
				break

	def createWidgets(self):
		"""Build GUI."""
		# Create Setup button
		#self.setup = Button(self.master, width=20, padx=3, pady=3)
		#self.setup["text"] = "Setup"
		#self.setup["command"] = self.setupMovie
		#self.setup.grid(row=1, column=0, padx=2, pady=2)

		self.choose = Button(self.master, width=20, padx=3, pady=3)
		self.choose["text"] = "Select film"
		self.choose["command"] = self.nextfilm
		self.choose.grid(row=1, column=0, padx=2, pady=2)
		
		# Create Play button		
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=1, padx=2, pady=2)
		
		# Create Pause button			
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=2, padx=2, pady=2)
		
		# Create Teardown button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=3, padx=2, pady=2)

		self.back = Button(self.master, width=20, padx=3, pady=3)
		self.back["text"] = "Back"
		self.back["command"] = lambda: self.pass_time(-2)
		self.back.grid(row=5, column=0, padx=2, pady=2)

		self.forward = Button(self.master, width=20, padx=3, pady=3)
		self.forward["text"] = "Forward"
		self.forward["command"] = lambda: self.pass_time(2)
		self.forward.grid(row=5, column=1, padx=2, pady=2)

		self.desc = Button(self.master, width=20, padx=3, pady=3)
		self.desc["text"] = "Description"
		self.desc["command"] = self.description
		self.desc.grid(row=5, column=2, padx=2, pady=2)

		self.start_time=Label(self.master,text=str(datetime.timedelta(seconds=0)))
		self.start_time.grid(row=4,column=0,sticky='ew')
		self.end_time=Label(self.master,text=str(datetime.timedelta(seconds=0)))
		self.end_time.grid(row=4,column=3,sticky='ew')

		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 

	def nextfilm(self):
		if self.state != self.PLAYING:
			if self.played == 0:
				self.delayfunc(float(0.4))
				self.playMovie()

			if self.played == 1:
				self.breakpoint = 1
				self.played = 0

				if self.teardownAcked == 0:
					self.delayfunc(float(0.1))
					self.exitClient()
				
				self.delayfunc(float(1))
				self.connectToServer() #TCP close()
				self.breakpoint = 0
				self.delayfunc(float(0.5))
				print(self.teardownAcked)

			self.index += 1
			if self.index == len(self.listfilm):
				self.index = 0
			self.fileName = self.listfilm[self.index]
			self.state = self.INIT
			self.choose["text"] = "File: " + str(self.fileName)
			self.setupMovie()

	def pass_time(self, time):
		#self.playEvent.set()
		self.index_frame=int(float(self.my_slider.get())*20) + time*20

		if self.index_frame < 0:
			self.index_frame = 0

		if self.state == self.PLAYING:
			self.pauseMovie()
			self.delayfunc(float(0.05))
			self.sendRtspRequest(self.SKIP)
			self.delayfunc(float(0.05))
			self.playMovie()
			self.delayfunc(float(0.05))
	def setupMovie(self):
		"""Setup button handler."""
		if self.state == self.INIT:
			self.delayfunc(float(0.4))
			self.removed = 0
			self.sendRtspRequest(self.SETUP)
	def description(self):
		if self.state != self.INIT:
			self.sendRtspRequest(self.DESCRIPTION)
	def exitClient(self):
		"""Teardown button handler."""
		self.sendRtspRequest(self.TEARDOWN)
		print("Video data rate: " + str(self.rate) + "bytes/sec")
		print("Data lost: " + str(self.lost))
	def pauseMovie(self):
		"""Pause button handler."""
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)
			self.paused = 1
	def playMovie(self):
		"""Play button handler."""
		#self.setupMovie()
		if self.state == self.READY:
			# Create a new thread to listen for RTP packets
			self.teardownAcked = 0
			self.sendRtspRequest(self.PLAY)
	def listenRtp(self):
		"""Listen for RTP packets."""
		while True:# Ngừng nghe khi yêu cầu PAUSE hoặc TEARDOWN rtp
			self.playEvent.wait(0.01)
			if self.playEvent.isSet(): 
				break
			if self.teardownAcked == 1:
				if self.removed == 0:
					os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video
					print("removed listen")
					self.removed = 1
					self.sessionId = 0
				self.rtpSocket.close()
				print("removed listen")
				break
			else:
				try:
					data, address = self.rtpSocket.recvfrom(20480) # < send <= 14000 bytes
					if data:
						rtpPacket = RtpPacket()
						rtpPacket.decode(data)
						self.rate = len(data)*20
						#print ("CURRENT SEQUENCE NUM: " + str(currFrameNbr))
											
						self.frameNbr = rtpPacket.seqNum()
						self.my_slider.set(self.frameNbr*0.05)
						self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
						self.slider_label['text']=str(datetime.timedelta(seconds=self.my_slider.get()))
				except:
					self.lost += 1							
	def writeFrame(self, data):
		"""Ghi khung nhận được vào tệp hình ảnh tạm thời. Trả lại tệp hình ảnh."""
		cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
		file = open(cachename, "wb")
		file.write(data)
		file.close()
		
		return cachename	
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		photo = ImageTk.PhotoImage(Image.open(imageFile))
		self.label.configure(image = photo, height=288) 
		self.label.image = photo		
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)#TCP
		try:
			self.rtspSocket.connect((self.serverAddr, self.serverPort))
		except:
			tkinter.messagebox.showerror("Error connection", "Connect to serverAddress " + str(self.serverAddr) + " is fail!")
			self.rtspSocket.close()
			self.master.destroy()	
	def sendRtspRequest(self, requestCode):

		"""Send RTSP request to the server."""
		# Setup request
		request = ""
		if requestCode == self.SKIP and self.state != self.INIT:
			self.rtspSeq+=1
		
			# Write the RTSP request to be sent.
			request += "%s %s %s" % (self.SKIP_STR, self.fileName, self.RTSP_VER)
			request +="\nCSeq: %d" % self.rtspSeq
			request +="\nSession: %d" % self.sessionId
			request +="\nindex_frame: %d\n" % (self.index_frame)

			self.requestSent = self.SKIP
			self.state = self.READY

		elif  requestCode == self.SETUP and self.state == self.INIT:
			self.threadrecv = threading.Thread(target=self.recvRtspReply)
			self.threadrecv.start()
			# Update RTSP sequence number.
			self.rtspSeq +=1
			
			# Write the RTSP request to be sent.
			request = "%s %s %s" % (self.SETUP_STR, self.fileName, self.RTSP_VER)
			request+="\nCSeq: %d" % self.rtspSeq
			request+="\nTransport: %s; client_port= %d" % (self.TRANSPORT,self.rtpPort)
			self.requestSent = self.SETUP
		# Play request
		elif requestCode == self.PLAY and self.state == self.READY:
			# Update RTSP sequence number.
			self.rtspSeq += 1
			self.played = 1
        
			# Write the RTSP request to be sent.
			request = "%s %s %s" % (self.PLAY_STR,self.fileName,self.RTSP_VER)
			request+="\nCSeq: %d" % self.rtspSeq
			request+="\nSession: %d"%self.sessionId
                
			
			# Keep track of the sent request.
			self.requestSent = self.PLAY
        # Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			# Update RTSP sequence number.
			self.rtspSeq+=1
			request = "%s %s %s" % (self.PAUSE_STR,self.fileName,self.RTSP_VER)
			request+="\nCSeq: %d" % self.rtspSeq
			request+="\nSession: %d"%self.sessionId
			
			self.requestSent = self.PAUSE
			# The play thread exits. A new thread is created on resume.
			self.playEvent.set()
			
		# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
			# Update RTSP sequence number.
			self.rtspSeq += 1
			# Write the RTSP request to be sent.
			request = "%s %s %s" % (self.TEARDOWN_STR, self.fileName, self.RTSP_VER)
			request+="\nCSeq: %d" % self.rtspSeq
			request+="\nSession: %d" % self.sessionId
			# The play thread exits. A new thread is created on resume.
			
			self.requestSent = self.TEARDOWN

		elif requestCode == self.DESCRIPTION and self.state != self.INIT:
			self.requestSent = self.DESCRIPTION
			#message request
			request = "DESCRIPTION " + str(self.fileName) + " RTSP/1.0\n"
			request += "CSeq: " + str(self.rtspSeq)
			request += "\nSession: " + str(self.sessionId)
		else:
			return
		
		# Gửi yêu cầu RTSP bằng rtspSocket.
		print ('\nData Sent:' + request)
		self.rtspSocket.send(request.encode())#create in connectToServer			
	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		while True:
			try:
				reply = self.rtspSocket.recv(256)
				
				if reply: 
					self.parseRtspReply(reply)

				if self.requestSent == self.TEARDOWN:
					if self.removed == 0 and self.breakpoint == 0 or self.removed == 0 and self.paused == 1:
						if self.removed == 0:
							os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video
							print("removed recv")
							self.removed = 1
						self.sessionId = 0
						self.paused = 0
						print("removed recv")
						
					self.rtspSocket.close()
					print("removed recv")
					break
			except:
				if self.requestSent == self.TEARDOWN:
					if self.removed == 0 and self.breakpoint == 0 or self.removed == 0 and self.paused == 1:
						if self.removed == 0:
							os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video
							print("removed recv")
						self.removed = 1
						self.sessionId = 0
						self.paused = 0
						print("removed recv")
						
					self.rtspSocket.close()
					print("removed recv")
					break
			
			# Close the RTSP socket upon requesting Teardown
	def parseRtspReply(self, data):
		"""Parse the RTSP reply from the server."""
		lines = data.decode().split('\n')
		seqNum = int(lines[1].split(' ')[1])
		totaltime= float(lines[3].split(' ')[1])

		#Chỉ xử lý nếu số thứ tự của câu trả lời của máy chủ giống với số thứ tự của yêu cầu
		if seqNum == self.rtspSeq:
			session = int(lines[2].split(' ')[1])
			# New RTSP session ID
			if self.sessionId == 0:
				self.sessionId = session
			# Chỉ xử lý nếu ID phiên giống nhau
			if self.sessionId == session:
				if int(lines[0].split(' ')[1]) == 200: 
					if self.requestSent == self.SETUP:
						if self.state == self.INIT:
							# Liên kết ổ cắm với địa chỉ bằng cách sử dụng cổng RTP do người dùng máy khách cung cấp.
							self.state = self.READY
							self.rate = 0
							self.lost= 0
							self.end_time["text"] = str(datetime.timedelta(seconds=totaltime))
							v = datetime.timedelta()
							self.my_slider=Scale(self.master,variable = v,from_=0,to=totaltime,orient=HORIZONTAL)

							self.my_slider.grid(row=2,column=0,columnspan=4,sticky='ew')

							self.slider_label=Label(self.master,text='0')
							self.slider_label.grid(row=3, columnspan=4, sticky='ew')
							# Open RTP port.
							self.openRtpPort() 

					elif self.requestSent == self.PLAY and self.state == self.READY:
						self.state = self.PLAYING
						self.playEvent = threading.Event()
						self.threadlisten = threading.Thread(target=self.listenRtp)
						self.threadlisten.start()

					elif self.requestSent == self.PAUSE and self.state == self.PLAYING:
						self.state = self.READY
					elif self.requestSent == self.TEARDOWN and self.state != self.INIT:
						self.state = self.INIT
						self.teardownAcked = 1
					elif self.requestSent == self.SKIP and self.state != self.INIT:
						self.state = self.READY
					elif self.requestSent == self.DESCRIPTION:
						if self.state != self.INIT:
							print("Description session: " + str(self.sessionId))
							for x in lines[4:]:
								print(x)	
	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		# Tạo một ổ cắm datagram mới để nhận các gói RTP từ máy chủ 
		self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		
		try:
			self.rtpSocket.bind(('',self.rtpPort))
		except:
			tkinter.messagebox.showwarning("UDP warning", "Can't blind to Port: " + str(self.rtpPort))
			self.rtpSocket.shutdown(socket.SHUT_RDWR)
			self.state = self.INIT
			self.rtpSocket.close()
		# Đặt giá trị thời gian chờ của ổ cắm thành 0,5 giây
		self.rtpSocket.settimeout(0.5)
	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		self.pauseMovie()
		if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
			if self.teardownAcked != 1:
				self.exitClient()
			self.master.destroy() # Close the gui window
		else: # When the user presses cancel, resume playing.
			self.playMovie()
