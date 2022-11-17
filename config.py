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

'''server'''
# server ip
SERVER_IP = '10.222.204.177'
# SERVER_IP = '8.218.117.184'
# SERVER_IP = 'localhost'
# welcome socket port
# connection socket will increase from this
# it's set casually on available port in the computer
SERVER_PORT = 8888

'''sender'''
# default retransmission time, if ping failed, use this
# ref: https://zhidao.baidu.com/question/1989362613706374707.html
# abstract: fine network delay is 1-100 ms
CONG_DEFAULT_TIMEOUT = 0.1
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
WRITE_MAX = 43
# receiver window
# it's set casually
RWND = 200

'''debug'''
# print some info during rdt transfer
DEBUG = True
# print performance such as rate and pkt_loss_rate
PERFORMANCE = True
