from rdt import *
from config import *
import socket

class Client(rdt):
    
    def __init__(self):
        '''create socket'''
        rdt.__init__(self)
        self.server_addr = (SERVER_IP, SERVER_PORT)

    def connect(self, server_addr=(SERVER_IP, SERVER_PORT)):
        '''handshake with welcome_socket and get server_port'''
        self.server_addr = server_addr
        while True:
            # handshake 1
            sndpkt = self.make_pkt(seq=1,issyn=1)
            self.udt_send(sndpkt, self.server_addr)
            # handshake 2
            rcvpkt, addr = self.rdt_rcv()
            length, seq, ack, isfin, issyn, data = self.extract(rcvpkt)
            if not issyn: continue
            # handshake 3
            re_sndpkt = self.make_pkt(seq=2,issyn=1)
            self.udt_send(re_sndpkt, self.server_addr)
            # get server_port
            self.server_addr = (self.server_addr[0], int(data.decode()[:length]))
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
            if i == 1 and op == 'frcv': # download file
                self.rdt_download_file(dest_path, self.server_addr)
            else: # upload file
                self.rdt_upload_file(source_path, self.server_addr)
        # sleep(5)

    def close(self):
        '''close socket'''
        self.socket.close()

def main():
    # client socket
    client_socket = Client()
    # 3 handshakes and connect
    client_socket.connect((SERVER_IP, SERVER_PORT))
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
