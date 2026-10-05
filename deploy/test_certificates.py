"""Exercise TLS trust, hostname and mandatory client authentication without TCP ports."""
import socket
import ssl
import tempfile
import threading
import unittest
from pathlib import Path
from .certificates import create


class CertificatesTest(unittest.TestCase):
    def test_mutual_tls_and_private_key_separation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'tls'
            create(root, '192.168.106.10')
            self.assertEqual({p.name for p in (root / 'app').iterdir()}, {'app.key', 'app.crt', 'server-ca.crt'})
            self.assertEqual({p.name for p in (root / 'runner').iterdir()}, {'runner.key', 'runner.crt', 'client-ca.crt'})
            for file in root.rglob('*'):
                self.assertEqual(file.stat().st_mode & 0o777, 0o700 if file.is_dir() else 0o600)
            with self.assertRaises(FileExistsError):
                create(root, '192.168.106.10')
            server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            server.load_cert_chain(root / 'runner/runner.crt', root / 'runner/runner.key')
            server.load_verify_locations(root / 'runner/client-ca.crt')
            server.verify_mode = ssl.CERT_REQUIRED

            def exchange(client_certificate=True, hostname='192.168.106.10'):
                client = ssl.create_default_context(cafile=root / 'app/server-ca.crt')
                if client_certificate:
                    client.load_cert_chain(root / 'app/app.crt', root / 'app/app.key')
                left, right = socket.socketpair()
                left.settimeout(2)
                right.settimeout(2)
                accepted = []

                def serve():
                    try:
                        with server.wrap_socket(left, server_side=True) as stream:
                            accepted.append(stream.getpeercert())
                            stream.sendall(b'ok')
                    except (ssl.SSLError, OSError):
                        pass
                    finally:
                        left.close()
                thread = threading.Thread(target=serve)
                thread.start()
                received = b''
                try:
                    with client.wrap_socket(right, server_hostname=hostname) as stream:
                        received = stream.recv(2)
                except (ssl.SSLError, OSError):
                    pass
                finally:
                    right.close()
                    thread.join(timeout=3)
                self.assertFalse(thread.is_alive())
                return received, accepted

            self.assertEqual(exchange()[0], b'ok')
            self.assertEqual(exchange(False), (b'', []))
            self.assertEqual(exchange(hostname='192.168.106.11')[0], b'')


if __name__ == '__main__':
    unittest.main()
