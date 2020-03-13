"""Some code taken from (or inspired by): https://docs.python.org/3/howto/sockets.html
                                          https://docs.python.org/3/library/socket.html
                                          https://docs.python.org/3/library/select.html
                                          http://beej.us/guide/bgnet/html/
                                          https://tools.ietf.org/html/rfc2616
                                          https://docs.python.org/3/library/multiprocessing.html"""  
                                                 
# import standard library items
import sys
import os
import socket
import select
import multiprocessing

# global constants
SERVER_ADDRESS = ''
SERVER_PORT = 8000
DATA_SIZE = 8192
FILE_READ_SIZE = 10485760
STATIC_FILE_PREFIX = b'static'


# class for handling and parsing HTTP requests
class HTTP_Request:
  
  def populate_headers(self, header_data: bytes):
    headers = header_data.split(b'\n')
   
    for head in headers:
    
      if not head:
        continue
      
      index = head.find(b':')
      
      if index < 0:
        print('header parse error')
        continue
        
      self.headers[head[:index].strip(b' \r\n')] = head[index + 1:].strip(b' \r\n')

  
  def parse_path_data(self, path_data: bytes):
    index = path_data.find(b'?')
    
    if index < 0:
      print('no query data')
      self.path = path_data
      return
    
    self.path = path_data[:index]
    
    query_data = (path_data[index + 1:]).split(b'&')
    
    for query in query_data:
      index2 = query.find(b'=')
     
      if index2 < 0:
        print('incomplete query')
        continue
        
      self.query[query[:index2].strip(b' \r\n')] = query[index2 + 1:].strip(b' \r\n')
      
  
  def __init__(self):
    self.method = b''
    self.path = b''
    self.query = {}
    self.headers = {}
    self.body = b''
    

# class for handling and assembling HTTP responses
class HTTP_Response:

  def add_header(self, name: str, value: str):
    self.headers[name] = value
  
  def __init__(self):
    self.version = 'HTTP/1.1'
    self.status = 0
    self.message = ''
    self.headers = {}
    self.body = ''
    
  def to_bytes(self):
    first_part = (self.version.encode('ascii') + b' ' + str(self.status).encode('ascii') + b' '
                  + self.message.encode('ascii') + b'\r\n')
     
    second_part = ''
    
    for key, value in self.headers.items():
      second_part = ''.join([second_part, key + ': ' + value + '\r\n'])
      
    second_part = ''.join([second_part, '\r\n']).encode('ascii')
    
    third_part = self.body.encode('utf-8')
    
    return b''.join([first_part, second_part, third_part])
    

# class for preserving state in client sockets
class ClientSocketState:
  
  def __init__(self, sock: socket.socket):
    self.socket = sock
    self.data_received = b''
    self.request = HTTP_Request()
    self.response = HTTP_Response()
  
  
# the main program function
def main():
   
  # create a listening socket for the server
  listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  
  # now, bind the socket to a local IP address and unused port
  listen_socket.bind((SERVER_ADDRESS, SERVER_PORT))
  
  # start listening for connections
  listen_socket.listen()
  
  # make the socket non-blocking
  listen_socket.setblocking(False)
  
  # print debug info
  sys.stderr.write('Sever listening on address {} and on port {}\n\n'.format(SERVER_ADDRESS, SERVER_PORT))
  
  # listen for and handle connections
  while True:

    # check if the socket is ready
    can_read, can_write, has_errors = select.select([listen_socket], [], [], 15)
    
    # check if the socket has an incoming connection
    if can_read:
    
      # handle new client connections
      client_socket, client_addr = listen_socket.accept()
      sys.stderr.write('\nAccepted Connection from {}\n\n'.format(str(client_addr)))
      
      # spin up a new process to handle the client's request
      client_socket.setblocking(False)
      client_handler = multiprocessing.Process(target=handle_clients, args=(client_socket,))
      client_handler.start()
      
      client_socket.close()

 

def handle_clients(sock: socket.socket):

  # save state data about the socket
  client_state = ClientSocketState(sock)
  
  # enter a data reception loop and attempt to gather all request info
  while True:
  
    # check if the socket is ready
    can_read, can_write, has_errors = select.select([sock], [], [], 15)
      
    # make sure the socket can be read
    if can_read:
    
      # handle reading initial data from each client socket     
      # try to get data. catch any weird errors
      try:
        recieved_data = sock.recv(DATA_SIZE)
      except Exception:
        sys.stderr.write('Client closed connection unexpectedly.\n')
        sock.close()
        break
        
      # make sure the client has not closed the connection already
      if len(recieved_data) > 0:
        client_state.data_received = b''.join([client_state.data_received, recieved_data])

        # guess to make sure basic connection information was sent before handling
        if (client_state.data_received.count(b'\r\n\r\n') > 0):
          
          # now, attempt to parse the received data
          check = parse_HTTP_header(client_state)
          
          if check != 0:
            sock.close()
            break
            
          parse_HTTP_request(client_state)
          
          # done with client, so cleanup and close connection
          sock.close()
          break
      
      # client already closed connection, so cleanup
      elif len(recieved_data) == 0:
        sys.stderr.write('Client closed connection.\n')
        sock.close()
        break
 
 
# handle HTTP headers 
def parse_HTTP_header(client: ClientSocketState) -> int:
  sys.stderr.write('\nReceived message from {}\nMessage Contents:\n{}\n\n'.format(client.socket.getpeername(), str(client.data_received)))
  
  # split request by line
  split_msg = client.data_received.split(b'\n')
  
  # assume that the request line is first, and split it by its components
  request_line_components = split_msg[0].split(b' ')
  
  # assumption checking
  if (len(request_line_components) < 3):
    sys.stderr.write('Error parsing request line.\n')
  
  # populate data
  client.request.method = request_line_components[0]
  client.request.parse_path_data(request_line_components[1])
  
  # guess for header data
  index2 = client.data_received.find(b'\r\n\r\n')
  
  if index2 < 0:
    return -1
 
  client.request.populate_headers(client.data_received[len(split_msg[0]):index2])
  
  # now populate any receieved body data
  client.request.body = b''.join([client.data_received[(index2 + 4):]])
  
  return 0


def parse_HTTP_request(client: ClientSocketState):

  # resolve automatic redirections
  resolve_automatic_redirects(client)
  
  # check for GET requests
  if client.request.method == b'GET':
      
    # send files unmodified
    send_static_file(client, STATIC_FILE_PREFIX)
   
  else:
    HTTP_404(client)
 
 
def send_static_file(client: ClientSocketState, start_path: bytes):

  # trim the leading slash
  file_name = client.request.path.strip(b'/')
  
  # try to open the file. send 404 if cannot open the file
  try:
    file = open(os.path.join(start_path, file_name), 'rb')
  except OSError:
    HTTP_404(client)
    return
  
  # get the size of the file
  file_size = os.path.getsize(os.path.join(start_path, file_name))
  
  # start forming the response
  client.response.status = 200
  client.response.message = 'OK'
  client.response.add_header('Connection', 'close')
  client.response.add_header('Content-Length', str(file_size))
  client.response.add_header('X-Content-Type-Options', 'nosniff')
  
  # set approriate MIME tags
  if file_name.endswith(b'.html'):
    client.response.add_header('Content-Type', 'text/html; charset=UTF-8')
  elif file_name.endswith(b'.js'):
    client.response.add_header('Content-Type', 'text/javascript; charset=UTF-8')
  elif file_name.endswith(b'.css'):
    client.response.add_header('Content-Type', 'text/css; charset=UTF-8')
  elif file_name.endswith(b'.png'):
    client.response.add_header('Content-Type', 'image/png')
  elif file_name.endswith(b'.bmp'):
    client.response.add_header('Content-Type', 'image/bmp')
  elif file_name.endswith(b'.gif'):
    client.response.add_header('Content-Type', 'image/gif')
  elif file_name.endswith(b'.jpg'):
    client.response.add_header('Content-Type', 'image/jpeg')

  # now, send the file on its way
  # first send the headers of the response
  send_data_over_socket(client.response.to_bytes(), client.socket)
  
  data_read = 0
  
  # loop over the file in chunks
  while data_read < file_size:
    data = file.read(FILE_READ_SIZE)
    data_read += len(data)
    send_data_over_socket(data, client.socket)
  
  file.close()
  
  
# valid redirect mapping
REDIRECTS = {b'/': b'/index.html'}
# resolve automatic redirections
def resolve_automatic_redirects(client: ClientSocketState):
  if client.request.path in REDIRECTS:
    client.request.path = REDIRECTS[client.request.path]


# HTTP Response Constants
HTTP_404_Page = b'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Length: 36\r\nConnection: close\r\n\r\nThe requested content was not found.'


# send a generic 404 page
def HTTP_404(client: ClientSocketState):
  send_data_over_socket(HTTP_404_Page, client.socket)
  

# send data over a socket, back to the client
def send_data_over_socket(data: bytes, sock: socket.socket):
  total_size = len(data)  
  sent_size = 0
  
  while sent_size < total_size:
    try:
      sent = sock.send(data[sent_size:])
    except BlockingIOError: # temporary error
      continue
    except Exception:
      sys.stderr.write('Client closed connection unexpectedly.\n')
      return
      
    sent_size += sent
    if sent == 0:
      sys.stderr.write('Send Error: Socket connection already closed.\n')
      break


# invoke the main function when running as the main script
if __name__ == "__main__":
  main()
    