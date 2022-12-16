from rdt import *

class Client(rdt):

    def __init__(self):
        '''create socket'''
        rdt.__init__(self)

    def connect(self, server_addr):
        '''handshake with welcome_socket and connect with connection socket'''
        self.server_addr = server_addr
        while True:
            # handshake 1
            sndpkt = self.make_pkt(seq=1,issyn=1)
            if DEBUG: print('handshake 1')
            rtt_beg = time.time()
            self.udt_send(sndpkt, self.server_addr)
            # handshake 2
            rcvpkt, addr = self.rdt_rcv()
            if DEBUG: print('handshake 2')
            rtt_end = time.time()
            length, seq, ack, isfin, issyn, txno, data = self.extract(rcvpkt)
            if not (issyn == 1): continue
            # handshake 3
            self.server_addr = (addr[0], int(data.decode()[:length]))
            re_sndpkt = self.make_pkt(seq=2,issyn=1)
            self.udt_send(re_sndpkt, self.server_addr)
            if DEBUG: print('handshake 3')
            break
        # send cong_timeout
        self.timeout = rtt_end - rtt_beg
        self.rwnd = math.floor(MAX_BANDWIDTH_Mbps * 1000000 * self.timeout / 8 / MSS)
        self.temp_filepath = 'client/temp/' + str(self.socket.getsockname()[1]) + '.txt'
        self.file = open(self.temp_filepath, 'w')
        self.file.write(f'{self.timeout} {self.rwnd}')
        self.file.close()
        self.rdt_upload_file(self.temp_filepath, self.server_addr, True)
        # print info
        print(f'>>> server {self.server_addr} connected')
        print(f'  > timeout={self.timeout} rwnd={self.rwnd}')
        print('>>> cmd')
        print('  > upload  : `fsnd filename`')
        print('  > download: `frcv filename`')
        print('  > exit    : input nothing:)')
        
    def rdt_transfer(self, op, filename):
        '''rdt send filename, then download or upload file'''
        # optimize judging uploading non-existing file here
        if op == 'fsnd' and os.path.isfile('client/' + filename) == False:
            print(f'file `client/{filename}` not exists or empty')
            return
        # upload or download file
        self.disconnect = False
        for i in range(2):
            # get path
            if i == 0: # send filename
                self.file = open(self.temp_filepath, 'w')
                self.file.write(op + ' ' + filename)
                self.file.close()
                source_path = self.temp_filepath
            else: # send file
                if op == 'fsnd': source_path = 'client/' + filename
                else: dest_path = 'client/' + filename[filename.rfind('/')+1:]
            # check if disconnected
            if self.disconnect:
                raise Exception(f'server is closed\nbye')
            # upload or download file
            if i == 0: # tempfile
                self.rdt_upload_file(source_path, self.server_addr, True)
            else: # file
                if op == 'frcv': # download file
                    self.rdt_download_file(dest_path, self.server_addr)
                    if os.path.isfile(dest_path):
                        print(f'download file `server/{filename}` to client folder')
                    else:
                        print(f'file `server/{filename}` not exists or empty')
                else: # upload file
                    self.rdt_upload_file(source_path, self.server_addr)
                    print(f'upload file `{source_path}` to server folder')
        
    def shutdown(self):
        '''send disconnect file'''
        self.file = open(self.temp_filepath, 'w')
        self.file.write('shutdown')
        self.file.close()
        self.socket.settimeout(1)
        self.rdt_upload_file(self.temp_filepath, self.server_addr, True)

def main():
    # client socket
    client_socket = Client()
    # 3 handshakes and connect
    try:
        client_socket.connect((SERVER_IP, SERVER_PORT))
        while True:
            line = input('>>> ')
            if line == '': # exit
                client_socket.shutdown()
                break
            cmd = line.split(' ') # analyze
            if (len(cmd) != 2) or (cmd[0] != 'fsnd' and cmd[0] != 'frcv'): # wrong cmd
                print('wrong cmd')
                continue
            client_socket.rdt_transfer(cmd[0], cmd[1]) # execute cmd
            # # limit one file download or upload each time
            client_socket.shutdown()
            break
    except Exception as e:
        print(str(e))
    # close client socket
    if DEBUG: print('bye')
    client_socket.close()

if __name__ == '__main__':
    main()
