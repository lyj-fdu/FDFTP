from rdt import *

class Server(rdt):
        
    def __init__(self, port):
        '''create socket'''
        rdt.__init__(self)
        self.socket.bind(('', port))
        self.connection_port = int(SERVER_PORT) + 1 # only used by welcome_socket
        
    def accept(self):
        '''welcome socket: 3 handshakes and prepare connection_socket'''
        # 3 handshakes
        while True:
            success = False
            # handshake 1
            rcvpkt, client_addr = self.rdt_rcv()
            length, seq, ack, isfin, issyn, data = self.extract(rcvpkt)
            if not (issyn == 1 and seq == 1): 
                sndpkt = self.make_pkt(issyn=0)
                self.udt_send(sndpkt, client_addr)
                continue
            # handshake 2
            self.client_addr = client_addr
            connection_port = str(self.connection_port)
            sndpkt = self.make_pkt(length=len(connection_port), issyn=1, data=connection_port.encode())
            self.udt_send(sndpkt, client_addr)
            # handshake 3
            re_rcvpkt, re_addr = self.rdt_rcv()
            re_length, re_seq, re_ack, re_isfin, re_issyn, re_data = self.extract(re_rcvpkt)
            if not (re_issyn == 1 and re_seq == 2 and client_addr == re_addr):
                sndpkt = self.make_pkt(issyn=0)
                self.udt_send(sndpkt, re_addr)
                continue
            break
        # prepare connection socket
        self.connection_port += 1
        return (self.connection_port - 1, client_addr)
    
    def connect(self, client_addr):
        '''connection socket: connect client'''
        self.client_addr = client_addr
        self.temp_filepath = 'server/temp/' + str(self.socket.getsockname()[1]) + '.txt'
    
    def rdt_transfer(self):
        '''connection socket: rdt receive filename, then upload or download file'''
        for i in range(2):
            # get path
            if i == 0: # save filename
                dest_path = self.temp_filepath
            else: # recieve file
                self.file = open(self.temp_filepath, 'r')
                cmd = str(self.file.read()).split(' ')
                op = cmd[0]
                filename = cmd[1]
                if op == 'fsnd': dest_path = 'server/' + filename
                else: source_path = 'server/' + filename
                self.file.close()
            if i == 1 and op == 'frcv': # upload file
                if os.path.isfile(source_path) == False:
                    while True:
                        sndpkt = self.make_pkt(length=0, seq=1, isfin=1)
                        self.udt_send(sndpkt, self.client_addr)
                        print("send     seq=1, fin")
                        rcvpkt, addr = self.rdt_rcv()
                        length, seq, ack, isfin, issyn, data = self.extract(rcvpkt)
                        if isfin == 1:
                            print("receive  finack")
                            self.send_base = self.PACKETS_NUM + 1
                            break
                else:
                    self.rdt_upload_file(source_path, self.client_addr)
            else: # download file
                if i == 0: self.socket.settimeout(RCV_TIMEOUT) # detect offline of client
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
