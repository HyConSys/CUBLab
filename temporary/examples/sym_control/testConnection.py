import socket


def check_server(ip, port):
   sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   sock.settimeout(5) 
   try:
       sock.connect((ip, port))
   except socket.error as e:
       print(f"No connection to {ip}:{port}. Error: {e}")
       return False
   else:
       print(f"Server {ip}:{port} is reachable!")
       return True
   finally:
       sock.close()


check_server('192.168.1.194', 12345)
check_server('192.168.1.144', 12345)