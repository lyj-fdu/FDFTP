# packet
PACKET_SIZE = 2000 # TCP packet size
BUFFER_SIZE = 2048 # receive packet buffer size

# client
CLIENT_IP = 'localhost'
# CLIENT_IP = '192.168.50.67'

# server
SERVER_IP = 'localhost'
# SERVER_IP = '192.168.50.10'
SERVER_PORT = 8888 # welcome socket port, connection socket will increase from this
CLIENT_TIMEOUT = 66 # if client has no movement in 66s, disconnect

# sender
CONG_TIMEOUT = 1 # sender retransmit after 1s
CONG_DEFALUT_SSTHRESH = 20.0 # if network is bad, set it small

# receiver
RCV_BUFSIZE = 66 # should be at least double the size of ssthresh

# debug
DEBUG = False # print some info
PERFORMANCE = True # print performance such as rate and pkt_loss_rate
