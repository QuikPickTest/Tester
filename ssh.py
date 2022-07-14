import paramiko

command = "tail -n 100 /data2/log/yitunnel-all.log"

# Update the next three lines with your
# server's information

host = "192.168.2.100"
username = "sandstar"
password = "Xe08v0Zy"
port = 45673

client = paramiko.client.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, port = port)
while(True):
    stdin, stdout, stderr = client.exec_command(command)
    print(stdout.read().decode())
client.close()

key_words = ['grpc open door', 'grpc close door', 'Order and Door is Closed!']
