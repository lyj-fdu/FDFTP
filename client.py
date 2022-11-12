from config import *
import struct
import os
import socket
from threading import Thread
from time import *

class Client:

    def __make_pkt(self, length=PACKET_SIZE, seq=0, ack=0, isfin=0, issyn=0, isack=0, data=' '.encode()):
        return struct.pack("6i" + str(PACKET_SIZE) + "s", length, seq, ack, isfin, issyn, isack, data)

    def __extract(self, rcvpkt):
        return struct.unpack("6i" + str(PACKET_SIZE) + "s", rcvpkt)
    
    def __rdt_send(self, size):
        return self.file.read(size)

    def __udt_send(self, sndpkt):
        self.socket.sendto(sndpkt, (self.server_ip, self.server_port))

    def __rdt_rcv(self):
        return self.socket.recvfrom(2048)
    
    def __deliver_data(self, receive_buffer):
        self.file.write(receive_buffer)
        self.file.flush()
        
    def __send_msg_pkt(self):
        '''send packets inside cwnd, GBN if timeout'''
        while True:
            # send all packets
            if self.PACKETS_NUM < self.send_base: break
            # timeout
            if CONG_TIMEOUT < (time() - self.timer):
                self.nextseqnum = self.send_base
                self.ssthresh = float(int(self.cwnd) // 2)
                if self.ssthresh < 1.0:
                    self.ssthresh = 1.0
                self.cwnd = 1.0
                self.timer = time()
                print("timeout! ssthresh=" + str(int(self.ssthresh)))
            # send packet
            if self.nextseqnum <= self.PACKETS_NUM and self.nextseqnum < self.send_base + int(self.cwnd):
                # buffer payload
                if self.bufferedseqnum < self.nextseqnum:
                    if self.nextseqnum == self.PACKETS_NUM:
                        self.send_buffer.append(self.__rdt_send(self.LAST_PACKET_SIZE))
                    else:
                        self.send_buffer.append(self.__rdt_send(PACKET_SIZE))
                    self.bufferedseqnum = self.nextseqnum
                # get payload
                payload = self.send_buffer[self.nextseqnum - self.send_base]
                # make packet
                if self.nextseqnum == self.PACKETS_NUM:
                    sndpkt = self.__make_pkt(length=self.LAST_PACKET_SIZE, seq=self.nextseqnum, isfin=1, data=payload)
                    if self.nextseqnum > self.sended:
                        print("send     seq=" + str(self.nextseqnum) + ", fin")
                        self.sended += 1
                    else:
                        print("resend   seq=" + str(self.nextseqnum) + ", fin")
                else:
                    sndpkt = self.__make_pkt(seq=self.nextseqnum, data=payload)
                    if self.nextseqnum > self.sended:
                        print("send     seq=" + str(self.nextseqnum) + ", cwnd=" + str(int(self.cwnd)))
                        self.sended += 1
                    else:
                        print("resend   seq=" + str(self.nextseqnum) + ", cwnd=" + str(int(self.cwnd)))
                # send packet
                self.__udt_send(sndpkt)
                # move next
                self.nextseqnum += 1

    def __receive_ack_pkt(self):
        '''receive ack_pkt, adjust timer and cwnd and send_buffer, shutdown if receive isfin'''
        while True:
            rcvpkt, addr = self.__rdt_rcv()
            length, seq, ack, isfin, issyn, isack, data = self.__extract(rcvpkt)
            if isfin == 0:
                print("receive  ack=" + str(ack))
                if ack == self.send_base:
                    self.send_buffer.pop(0)
                    self.timer = time()
                    self.send_base = ack + 1
                    if self.cwnd < self.ssthresh:
                        self.cwnd += 1.0
                    else:
                        self.cwnd += 1 / float(int(self.cwnd))
            else:
                print("receive  ack=" + str(ack) + ", finack")
                self.send_base = self.PACKETS_NUM + 1
                break

    def __receive_msg_pkt_and_send_ack_pkt(self):
        '''receive packet and send ack, until the whole file is acked'''
        while True:
            # self.socket.settimeout(RCV_TIMEOUT) # in prevention of client offline
            rcvpkt, client_addr = self.__rdt_rcv()
            length, seq, ack, isfin, issyn, isack, data = self.__extract(rcvpkt)
            if isfin == 0:
                # update ack, expectedseqnum, buffer
                if seq == self.expectedseqnum:
                    self.receive_buffer = self.receive_buffer + data[:length]
                    self.buffer_count += 1
                    if BUFFER_SIZE <= self.buffer_count:
                        self.__deliver_data(self.receive_buffer)
                        self.receive_buffer = bytes()
                        self.buffer_count = 0
                        print("flush")
                    ack = self.expectedseqnum
                    self.expectedseqnum += 1
                else:
                    if seq < self.expectedseqnum:
                        ack = seq
                    else:
                        ack = self.expectedseqnum - 1
                # send ack packet
                sndpkt = self.__make_pkt(ack=ack, isfin=isfin)
                self.__udt_send(sndpkt)
                print("send     ack=" + str(ack))
            else:
                print("receive  fin")
                # update ack, buffer
                if seq == self.expectedseqnum:
                    self.receive_buffer = self.receive_buffer + data[:length]
                    self.buffer_count += 1
                    self.__deliver_data(self.receive_buffer)
                    self.receive_buffer = bytes()
                    self.buffer_count = 0
                    print("flush")
                    ack = self.expectedseqnum
                else:
                    isfin = 0
                    if seq < self.expectedseqnum:
                        ack = seq
                    else:
                        ack = self.expectedseqnum - 1
                # send ack packet
                sndpkt = self.__make_pkt(ack=ack, isfin=isfin)
                self.__udt_send(sndpkt)
                if isfin == 0:
                    print("send     ack=" + str(ack))
                else:
                    print("send     ack=" + str(ack) + ", finack")
                    break
                
    def __rdt_upload_file(self, source_path):
        self.file = open(source_path, 'rb')
        self.FILE_SIZE = os.path.getsize(source_path)
        self.PACKETS_NUM = self.FILE_SIZE // PACKET_SIZE + 1
        self.LAST_PACKET_SIZE = self.FILE_SIZE - (self.PACKETS_NUM - 1) * PACKET_SIZE
        self.send_buffer = []
        self.timer = time()
        self.send_base = 1
        self.nextseqnum = 1
        self.bufferedseqnum = 0
        self.sended = 0
        self.ssthresh = DEFALUT_THRESHOLD
        self.cwnd = 1.0
        send = Thread(target=self.__send_msg_pkt)
        receive = Thread(target=self.__receive_ack_pkt)
        send.start()
        receive.start()
        send.join()
        receive.join()
        # close file
        self.file.close()
    
    def __rdt_download_file(self, dest_path):
        # clear old file
        try: os.remove(dest_path)
        except: pass
        # create file
        self.file = open(dest_path, 'w')
        self.file.close()
        # open file and receive
        self.file = open(dest_path, 'wb')
        self.receive_buffer = bytes()
        self.buffer_count = 0
        self.expectedseqnum = 1
        self.__receive_msg_pkt_and_send_ack_pkt()
        # close file
        self.file.close()
    
    def __init__(self):
        '''create socket'''
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def connect(self, server_ip=SERVER_IP, server_port=SERVER_PORT):
        '''handshake with welcome_socket and get server_port'''
        self.server_ip = server_ip
        self.server_port = server_port
        while True:
            # handshake 1
            sndpkt = self.__make_pkt(seq=1,issyn=1)
            self.__udt_send(sndpkt)
            # handshake 2
            rcvpkt, addr = self.__rdt_rcv()
            length, seq, ack, isfin, issyn, isack, data = self.__extract(rcvpkt)
            if not issyn: continue
            # handshake 3
            re_sndpkt = self.__make_pkt(seq=2,issyn=1)
            self.__udt_send(re_sndpkt)
            # get server_port
            self.server_port = int(data.decode()[:length])
            break

    def rdt_transfer(self, op, filename):
        '''rdt send filename, then download or upload file'''
        for i in range(2):
            # get path
            if i == 0: # send filename
                self.file = open('client/temp.txt', 'w')
                self.file.write(op + ' ' + filename)
                self.file.close()
                source_path = 'client/temp.txt'
            else: # send file
                if op == 'fsnd':
                    source_path = 'client/' + filename
                else:
                    dest_path = 'client/' + filename
            # download file
            if i == 1 and op == 'frcv':
                self.__rdt_download_file(dest_path)
            # upload file
            self.__rdt_upload_file(source_path)
        # sleep(5)

    def close(self):
        '''close socket'''
        self.socket.close()

def main():
    # client socket
    client_socket = Client()
    # 3 handshakes and connect
    client_socket.connect(SERVER_IP, SERVER_PORT)
    # send files
    while True:
        line = input('input `fsnd filename` to upload, or `frcv filename` to download, or nothing to exit:)\n')
        if line == '': break # exit
        cmd = line.split(' ') # analyze
        print(cmd)
        if (len(cmd) != 2) or (cmd[0] != 'fsnd' and cmd[0] != 'frcv'): continue # wrong cmd
        client_socket.rdt_transfer(cmd[0], cmd[1]) # execute cmd
    # close client socket
    client_socket.close()

if __name__ == "__main__":
    main()
