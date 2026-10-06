"""Install the Mac pull deployer from a reviewed checkout; does not enable GitHub CD."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess

from host import CONFIG, ROOT, storage
from release import PROTECTED


def install():
    os.umask(0o077)
    storage()
    source = Path(__file__).resolve().parent
    target = CONFIG / 'deployment'
    target.mkdir(exist_ok=True, mode=0o700)
    with (target / 'poll.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        node = shutil.which('node')
        if not node or subprocess.check_output([node, '--version'], text=True).split('.')[0] != 'v24':
            raise RuntimeError('Node 24 must be available before installation')
        for name in ['github_deploy.py', 'release.py', 'changes.py', 'host.py', 'check-host.py',
                     'runner-network.sb', 'runner-lima-override.yaml', 'monitor.py']:
            shutil.copyfile(source / name, target / name)
            (target / name).chmod(0o600)
        config = {'node_directory': str(Path(node).resolve().parent),
                  'protected': {name: hashlib.sha256((source.parent / name).read_bytes()).hexdigest() for name in PROTECTED}}
        (target / 'cd.json').write_text(json.dumps(config, indent=2) + '\n')
        app = Path.home() / 'Applications/Code Trainer Deploy.app'
        binary = app / 'Contents/MacOS/CodeTrainerDeploy'
        binary.parent.mkdir(parents=True, exist_ok=True)
        with (app / 'Contents/Info.plist').open('wb') as stream:
            plistlib.dump({'CFBundleExecutable': binary.name, 'CFBundleIdentifier': 'com.code-trainer.deploy-service',
                          'CFBundleName': 'Code Trainer Deploy', 'CFBundlePackageType': 'APPL',
                          'CFBundleVersion': '1', 'LSUIElement': True}, stream)
        subprocess.run(['xcrun', 'swiftc', str(source / 'service-launcher.swift'), '-o', str(binary)], check=True)
        subprocess.run(['codesign', '--force', '--sign', '-', str(app)], check=True)
        agent = Path.home() / 'Library/LaunchAgents/com.code-trainer.deploy.plist'
        log = CONFIG / 'deploy.log'
        log.touch(mode=0o600, exist_ok=True)
        with agent.open('wb') as stream:
            plistlib.dump({'Label': 'com.code-trainer.deploy', 'ProgramArguments': [str(binary), 'deploy'],
                          'StartInterval': 60, 'RunAtLoad': True, 'ThrottleInterval': 60,
                          'WorkingDirectory': str(Path.home()), 'ProcessType': 'Background', 'ExitTimeOut': 120,
                          'StandardOutPath': str(log), 'StandardErrorPath': str(log)}, stream)
        agent.chmod(0o600)
        domain = 'gui/' + str(os.getuid())
        # The lock prevents replacing an active deployer; reloading idle timer is safe.
        subprocess.run(['launchctl', 'bootout', domain + '/com.code-trainer.deploy'], capture_output=True)
        subprocess.run(['launchctl', 'bootstrap', domain, str(agent)], check=True)
        monitor_agent = agent.with_name('com.code-trainer.monitor.plist')
        with monitor_agent.open('wb') as stream:
            plistlib.dump({'Label': 'com.code-trainer.monitor', 'ProgramArguments': [str(binary), 'monitor'],
                          'StartInterval': 300, 'RunAtLoad': True, 'ThrottleInterval': 60,
                          'WorkingDirectory': str(Path.home()), 'ProcessType': 'Background',
                          'StandardOutPath': str(CONFIG / 'monitor.log'), 'StandardErrorPath': str(CONFIG / 'monitor.log')}, stream)
        monitor_agent.chmod(0o600)
        subprocess.run(['launchctl', 'bootout', domain + '/com.code-trainer.monitor'], capture_output=True)
        subprocess.run(['launchctl', 'bootstrap', domain, str(monitor_agent)], check=True)
    print('Installed 60-second deployment polling; enable ENABLE_CD in GitHub after verification.')


if __name__ == '__main__':
    install()
