'''server'''
# server ip
SERVER_IP = '8.210.99.245' # remote server
# SERVER_IP = '172.19.6.185' # remote server
# welcome socket port
# connection socket will increase from this
# it's set casually on available port in the computer
SERVER_PORT = 8888
# server maxium bandwith
MAX_BANDWIDTH_Mbps = 30.0
# tremble rate
TREMBLE_RATE = 1.3

'''debug'''
# print some info during rdt transfer
DEBUG = True
# print performance such as rate and pkt_loss_rate
PERFORMANCE = True

'''packet'''
# max segment size
# ref: https://juejin.cn/post/6884585578344480781
# abstract: UDP payload (1472) - 6i (24) = 1448
# NOTE: seq and ack are int in packet, 
#       which means can send up to roughly 2GB
#       we can set them to q(long long) to send more
MSS = 1400
# socket.recvfrom(BUFSIZE)
# ref: https://cloud.tencent.com/developer/article/2107386
# abstract: 2048 is enough, because ethernet transmits less than 1500 Bytes
BUFSIZE = 2048

'''sender'''
# default retransmission time, if ping failed, use this
# ref: https://zhidao.baidu.com/question/1989362613706374707.html
# abstract: fine network delay is 1-100 ms
# the real timeout is set by ping, if ping failed, use this default
DEFAULT_CONG_TIMEOUT = 0.1
# defalut ssthresh
# ref: https://www.cnblogs.com/virusolf/p/4332652.html
# abstract: Google says cwnd default to be 10.0 is best
DEFAULT_CWND = 10.0

'''receiver'''
# fixed-size receiver window
# how many pakets can recevier buffer before receive expectedseqnum
# ref: https://blog.csdn.net/qq_44404509/article/details/109467181
# abstract: it should be less than 65535 / 1448 = 45.3, 
#           or file.write() will envoke [Errno 5] Input/output error
# it's set casually, of course, the bigger, the better, only if <= 43
WRITE_MAX = 45
# receiver window
# ref: https://www.cnblogs.com/virusolf/p/4332652.html
# abstract: too small will not fully ues bandwidth
#           too big will cause stop-wait of TCP-NewReno if too many packets lost
# it's set casually of a medium number
DEFAULT_RWND = 200
