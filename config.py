'''packet'''
# max segment size
# ref: https://juejin.cn/post/6884585578344480781
# abstract: UDP payload (1472) - 5i (20) = 1452
# NOTE: seq and ack are int in packet, 
#       which means can send up to roughly 2GB
#       we can set them to q(long long) to send more
MSS = 1452
# socket.recvfrom(BUFSIZE)
# ref: https://cloud.tencent.com/developer/article/2107386
# abstract: 2048 is enough, because ethernet transmits less than 1500 Bytes
BUFSIZE = 2048

'''client'''
# client ip
# CLIENT_IP = 'localhost'
CLIENT_IP = '192.168.50.67'

'''server'''
# server ip
# SERVER_IP = 'localhost'
SERVER_IP = '192.168.50.10'
# welcome socket port
# connection socket will increase from this
# it's set casually on available port in the computer
SERVER_PORT = 8888
# disconnect time
# if client has no movement in CLIENT_TIMEOUT, disconnect
# it's set casually
CLIENT_TIMEOUT = 666

'''sender'''
# states of sender
SS = 'SS'
CA = 'CA'
FR = 'FR'
# retransmission time
# if the network is bad, set it smaller
# the better practice is to measure RTT and set dynamically
# but it's set casually right now
CONG_TIMEOUT = 1
# defalut ssthresh
# ref: https://blog.csdn.net/lishanmin11/article/details/77165077
# abstract: Google says cwnd default to be 10.0 is best
CONG_DEFALUT_SSTHRESH = 10.0

'''receiver'''
# fixed-size receiver window
# how many pakets can recevier buffer before receive expectedseqnum
# ref: https://blog.csdn.net/qq_44404509/article/details/109467181
# abstract: it should be less than 65535 / MSS ≈ 43, 
#           or file.write() will envoke [Errno 5] Input/output error
# it's set casually, of course, the bigger, the better, only if < 44
RWND = 43

'''debug'''
# print some info during rdt transfer
DEBUG = True
# print performance such as rate and pkt_loss_rate
PERFORMANCE = True
