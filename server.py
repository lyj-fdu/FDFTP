from rdt import *
from config import *
import socket
from threading import Thread

class Server(rdt):
        
    def __init__(self, port):
        '''create socket'''
        rdt.__init__(self)
        self.socket.bind(('', port))
        self.client_addr = (0, 0)
        # only used by welcome_socket
        self.connection_port = int(SERVER_PORT) + 1
        
    def accept(self):
        '''welcome socket: 3 handshakes and prepare connection_socket'''
        # 3 handshakes
        while True:
            success = False
            # handshake 1
            rcvpkt, client_addr = self.rdt_rcv()
            length, seq, ack, isfin, issyn, data = self.extract(rcvpkt)
            if (issyn != 1) or (seq != 1): continue
            # handshake 2
            self.client_addr = client_addr
            connection_port = str(self.connection_port)
            sndpkt = self.make_pkt(length=len(connection_port), issyn=1, data=connection_port.encode())
            self.udt_send(sndpkt, client_addr)
            # handshake 3
            re_rcvpkt, re_addr = self.rdt_rcv()
            re_length, re_seq, re_ack, re_isfin, re_issyn, re_data = self.extract(re_rcvpkt)
            if (re_issyn != 1) or (re_seq != 2) or (client_addr != re_addr): continue
            break
        # prepare connection socket
        self.connection_port += 1
        return (self.connection_port - 1, client_addr)
    
    def connect(self, client_addr):
        '''connection socket: connect client'''
        self.client_addr = client_addr
    
    def rdt_transfer(self):
        '''connection socket: rdt receive filename, then upload or download file'''
        for i in range(2):
            # get path
            if i == 0: # save filename
                dest_path = 'server/temp.txt'
            else: # recieve file
                self.file = open('server/temp.txt', 'r')
                cmd = str(self.file.read()).split(' ')
                op = cmd[0]
                filename = cmd[1]
                if op == 'fsnd':
                    dest_path = 'server/' + filename
                else:
                    source_path = 'server/' + filename
                self.file.close()
            if i == 1 and op == 'frcv': # upload file
                self.rdt_upload_file(source_path, self.client_addr)
            else: # download file
                self.rdt_download_file(dest_path, self.client_addr)

    def close(self):
        '''close socket'''
        self.socket.close()

def communicate(connection_port, client_addr):
    '''connection socket thread'''
    connection_socket = Server(connection_port)
    connection_socket.connect(client_addr)
    try:
        while True: # receive 1 file each time
            connection_socket.rdt_transfer()
    except Exception as e:
        connection_socket.close()
        print(str(e))

def main():
    # welcome socket
    welcome_socket = Server(SERVER_PORT)
    # listen
    try:
        while True:
            # 3 handshakes
            connection_port, client_addr = welcome_socket.accept()
            # connection socket works
            connection = Thread(target=communicate, args=(connection_port, client_addr))
            connection.start()
    except Exception as e:
        welcome_socket.close()
        print(str(e))

if __name__ == "__main__":
    main()
