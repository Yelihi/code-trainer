"""Live checks for the two Mac VMs; no paid AI calls or personal data output."""
import json
import os
import socket
import subprocess
import urllib.error
import urllib.request
from host import storage, ROOT, ENV

storage()
assert json.load(urllib.request.urlopen('http://127.0.0.1:8010/healthz', timeout=3)) == {'ok': True}
try:
    urllib.request.urlopen('http://127.0.0.1:8010/api/session', timeout=3)
    raise AssertionError('Unauthenticated API accepted')
except urllib.error.HTTPError as error:
    assert error.code == 401

app_probe = '''
import http.client, pathlib, shutil, ssl, urllib.request
from backend import runner
assert shutil.which('docker') is None
assert not pathlib.Path('/var/run/docker.sock').exists()
programs = {'javascript': 'console.log(42)', 'typescript': 'const n:number=42;console.log(n)',
            'python': 'print(42)', 'cpp': '#include <iostream>\\nint main(){std::cout<<42;}',
            'rust': 'fn main(){println!("42");}'}
for language, code in programs.items():
    result = runner.run(language, code, [''])[0]
    assert result['status'] == 'ok' and result['stdout'].strip() == '42', (language, result)
context = ssl.create_default_context(cafile='/tls/server-ca.crt')
try:
    urllib.request.urlopen('https://192.168.5.2:18443/runtime', context=context, timeout=3)
    raise AssertionError('Runner accepted client without a certificate')
except (ssl.SSLError, http.client.RemoteDisconnected):
    pass
except urllib.error.URLError as error:
    assert isinstance(error.reason, ssl.SSLError), error
print('PASS app without Docker; five languages over mTLS; unauthenticated runner rejected')
'''
subprocess.run(['docker', '--context', 'colima-code-trainer-app', 'exec', 'code-trainer-app',
                'python', '-c', app_probe], env=ENV, check=True)

# Establish a live control endpoint before testing its denial from the guest.
assert json.load(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3))['status'] == 'ok'
guest_probe = '''
import socket, subprocess
socket.setdefaulttimeout(2)
for host, port in [('192.168.7.2',8000),('192.168.7.2',8010),('192.168.5.3',22),('1.1.1.1',443)]:
    with socket.socket() as connection:
        assert connection.connect_ex((host,port)) != 0, ('Unexpected VM egress',host,port)
mounted = subprocess.run(['findmnt','-rn','-t','virtiofs,9p'],capture_output=True,text=True)
assert not mounted.stdout, 'Host filesystem is shared with runner'
assert not __import__('pathlib').Path('/sys/class/net/col0').exists(), 'Second NIC bypasses host network policy'
print('PASS runner root cannot reach Mac services, app network or Internet; no host mounts/second NIC')
'''
subprocess.run(['colima', '-p', 'code-trainer-runner', 'ssh', '--', 'sudo', 'python3', '-c', guest_probe],
               env={**ENV, 'COLIMA_HOME': str(ROOT / 'rvm')}, check=True)
with socket.socket() as connection:
    connection.settimeout(2)
    assert connection.connect_ex(('127.0.0.1',8443)) != 0, 'Runner port was automatically forwarded'
print('PASS Mac health/authentication, retained resume-agent health, and disabled automatic runner forwarding')
