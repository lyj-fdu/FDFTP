from rdt import *

class Server(rdt):
    def __init__(self, port):
        '''create socket'''
        rdt.__init__(self)
        self.socket.bind(('', port))

class WelcomeServer(Server):

    def __init__(self, port):
        '''create socket and connection_port'''
        Server.__init__(self, port)
        self.connection_port = int(SERVER_PORT) + 1
        self.temp_filepath = 'server/temp/' + str(self.socket.getsockname()[1]) + '.txt'

    def accept(self):
        '''3 handshakes and prepare connection_socket'''
        while True:
            # handshake 1
            rcvpkt, client_addr = self.rdt_rcv()
            length, seq, ack, isfin, issyn, txno, data = self.extract(rcvpkt)
            if DEBUG: print('handshake 1')
            if not (issyn == 1 and seq == 1): 
                sndpkt = self.make_pkt(issyn=0)
                self.udt_send(sndpkt, client_addr)
                continue
            # handshake 2
            connection_port = str(self.connection_port)
            sndpkt = self.make_pkt(length=len(connection_port), issyn=1, data=connection_port.encode())
            self.udt_send(sndpkt, client_addr)
            if DEBUG: print('handshake 2')
            break
        self.connection_port += 1
        return self.connection_port - 1

class ConnectionServer(Server):

    def __init__(self, port):
        '''create socket'''
        Server.__init__(self, port)

    def connect(self):
        '''connect client'''
        # handshake 3
        rcvpkt, client_addr = self.rdt_rcv()
        length, seq, ack, isfin, issyn, txno, data = self.extract(rcvpkt)
        if DEBUG: print('handshake 3')
        print(f'>>> {client_addr} connected')
        # connect with client socket
        self.client_addr = client_addr
        self.temp_filepath = 'server/temp/' + str(self.socket.getsockname()[1]) + '.txt'
        self.rdt_download_file(self.temp_filepath, self.client_addr)
        self.file = open(self.temp_filepath, 'r')
        content = str(self.file.read()).split(' ')
        if len(content) != 2:
            if DEBUG: print(content)
            raise Exception('get info fail, client fail to connect')
        self.CONG_TIMEOUT = float(content[0])
        self.RWND = int(content[1])
        self.file.close()

    def rdt_transfer(self):
        '''rdt receive filename, then upload or download file'''
        # upload or download file
        for i in range(2):
            # get path
            if i == 0: # save filename
                dest_path = self.temp_filepath
            else: # recieve file
                self.file = open(self.temp_filepath, 'r')
                cmd = str(self.file.read())
                if cmd == 'shutdown':
                    self.file.close()
                    raise Exception('client shutdown')
                cmd = cmd.split(' ')
                if (len(cmd) != 2) or (cmd[0] != 'fsnd' and cmd[0] != 'frcv'): # wrong cmd
                    if DEBUG: print(cmd)
                    raise Exception('client fail to connect')
                op = cmd[0]
                filename = cmd[1]
                if op == 'fsnd': dest_path = 'server/' + filename[filename.rfind('/')+1:]
                else: source_path = 'server/' + filename
                self.file.close()
            # upload or download file
            if i == 0: # tempfile
                self.rdt_download_file(dest_path, self.client_addr)
            else: # file
                if op == 'frcv': # upload file
                    self.rdt_upload_file(source_path, self.client_addr)
                else: # download file
                    self.rdt_download_file(dest_path, self.client_addr)

def communicate(connection_port):
    '''connection socket thread'''
    # connection socket
    connection_socket = ConnectionServer(connection_port)
    # connect
    try:
        connection_socket.connect()
        while True: # receive 1 file each time
            connection_socket.rdt_transfer()
    except Exception as e:
        print(str(e))
    # close connection socket
    connection_socket.close()

def main():
    # welcome socket
    welcome_socket = WelcomeServer(SERVER_PORT)
    # listen
    try:
        while True:
            # 3 handshakes
            connection_port = welcome_socket.accept()
            # connection socket works
            connection = threading.Thread(target=communicate, args=(connection_port,))
            connection.start()
    except Exception as e:
        print(str(e))
    # close welcome socket
    welcome_socket.close()

if __name__ == '__main__':
    main()
