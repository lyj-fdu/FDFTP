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
            length, seq, ack, isfin, issyn, data = self.extract(rcvpkt)
            # handshake 2 & 3
            if issyn == 1:
                try:
                    cong_timeout = max(float(ping(str(client_addr[0]))) * 3 / 1000, CONG_DEFAULT_TIMEOUT)
                except:
                    cong_timeout = CONG_DEFAULT_TIMEOUT
                self.file = open(self.temp_filepath, 'w')
                self.file.write(f'{self.connection_port} {cong_timeout}')
                self.file.close()
                self.rdt_upload_file(self.temp_filepath, client_addr, True)
                break
        self.connection_port += 1
        return (self.connection_port - 1, client_addr, cong_timeout)

class ConnectionServer(Server):

    def __init__(self, port):
        '''create socket'''
        Server.__init__(self, port)

    def connect(self, client_addr, cong_timeout):
        '''connect client'''
        # connect with client socket
        self.client_addr = client_addr
        self.cong_timeout = cong_timeout
        self.temp_filepath = 'server/temp/' + str(self.socket.getsockname()[1]) + '.txt'

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

def communicate(connection_port, client_addr, cong_timeout):
    '''connection socket thread'''
    # connection socket
    connection_socket = ConnectionServer(connection_port)
    # connect
    connection_socket.connect(client_addr, cong_timeout)
    print(f'>>> {client_addr} connected')
    if DEBUG: print(f'congestion timeout={cong_timeout}')
    try:
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
            connection_port, client_addr, cong_timeout = welcome_socket.accept()
            # connection socket works
            connection = threading.Thread(target=communicate, args=(connection_port, client_addr, cong_timeout))
            connection.start()
    except Exception as e:
        print(str(e))
    # close welcome socket
    welcome_socket.close()

if __name__ == '__main__':
    main()
