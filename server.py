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
            # handshake 2 & 3
            if issyn == 1:
                self.transaction_no = -1
                self.file = open(self.temp_filepath, 'w')
                self.file.write(f'{self.connection_port}')
                self.file.close()
                self.rdt_upload_file(self.temp_filepath, client_addr, True)
                break
        self.connection_port += 1
        return (self.connection_port - 1, client_addr)

class ConnectionServer(Server):

    def __init__(self, port):
        '''create socket'''
        Server.__init__(self, port)

    def connect(self, client_addr):
        '''connect client'''
        # connect with client socket
        self.transaction_no = 0
        self.client_addr = client_addr
        self.temp_filepath = 'server/temp/' + str(self.socket.getsockname()[1]) + '.txt'
        self.rdt_download_file(self.temp_filepath, self.client_addr)
        self.file = open(self.temp_filepath, 'r')
        content = str(self.file.read()).split(' ')
        if len(content) != 2:
            if DEBUG: print(content)
            raise Exception('client fail to connect')
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

def communicate(connection_port, client_addr):
    '''connection socket thread'''
    # connection socket
    connection_socket = ConnectionServer(connection_port)
    # connect
    try:
        connection_socket.connect(client_addr)
        print(f'>>> {client_addr} connected')
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
            connection_port, client_addr = welcome_socket.accept()
            # connection socket works
            connection = threading.Thread(target=communicate, args=(connection_port, client_addr))
            connection.start()
    except Exception as e:
        print(str(e))
    # close welcome socket
    welcome_socket.close()

if __name__ == '__main__':
    main()
