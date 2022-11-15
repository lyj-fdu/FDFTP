'''packet'''
# max segment size
# ref: https://juejin.cn/post/6884585578344480781
# abstract: UDP payload (1472) - 5i (20) = 1452
# NOTE: seq and ack are int in packet, 
#       which means can send up to roughly 2GB
#       we can set them to q(long long) to send more
MSS = 1452
# socket.recvfrom(BUFFER_SIZE)
# ref: https://cloud.tencent.com/developer/article/2107386
# abstract: 2048 is enough, because ethernet transmits less than 1500 Bytes
BUFFER_SIZE = 2048

'''client'''
# client ip
# CLIENT_IP = 'localhost'
CLIENT_IP = '10.219.150.142'

'''server'''
# server ip
# SERVER_IP = 'localhost'
SERVER_IP = '10.219.226.57'
# welcome socket port
# connection socket will increase from this
# it's set randomly on available port in the computer
SERVER_PORT = 8888
# disconnect time
# if client has no movement in 66s, disconnect
# it's set randomly
CLIENT_TIMEOUT = 66

'''sender'''
# retransmission time
# if the network is bad, set it smaller
# it's set randomly right now, but the better practice is to measure RTT and set dynamically
CONG_TIMEOUT = 1
# defalut ssthresh
# ref: https://blog.csdn.net/lishanmin11/article/details/77165077
# abstract: Google says cwnd default to be 10.0 is best
CONG_DEFALUT_SSTHRESH = 10.0

'''receiver'''
# how many pakets can recevier buffer before receive expectedseqnum
# ref: https://blog.csdn.net/qq_44404509/article/details/109467181
# abstract: it should be less than 65535 / MSS ≈ 43, or os will be error
# it should be more than CONG_DEFALUT_SSTHRESH to ensure performance
# it's set randomly here
RCV_BUFSIZE = 36

'''debug'''
# print some info during rdt transfer
DEBUG = True
# print performance such as rate and pkt_loss_rate
PERFORMANCE = True
