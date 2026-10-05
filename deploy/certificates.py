"""Create separate client/server CAs for one app-to-runner link. Never overwrites keys."""
import argparse
from datetime import datetime, timedelta, timezone
import ipaddress
from pathlib import Path
import os
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def create(destination, address):
    address = ipaddress.ip_address(address)
    if not address.is_private or address.is_loopback or address.is_unspecified:
        raise ValueError('Use the runner VM private IP, not loopback or a public address')
    destination = Path(destination)
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    for name in ('authority', 'app', 'runner'):
        (destination / name).mkdir(mode=0o700)
    now = datetime.now(timezone.utc)

    def save(path, data):
        with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as file:
            file.write(data)

    def issue(name, issuer=None, usage=None):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
        cert = (x509.CertificateBuilder().subject_name(subject)
                .issuer_name(issuer[1].subject if issuer else subject).public_key(key.public_key())
                .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=5))
                .not_valid_after(now + timedelta(days=90 if issuer else 365))
                .add_extension(x509.BasicConstraints(ca=issuer is None, path_length=0 if issuer is None else None), critical=True)
                .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                    key_encipherment=issuer is not None, data_encipherment=False, key_agreement=False,
                    key_cert_sign=issuer is None, crl_sign=issuer is None, encipher_only=None, decipher_only=None), critical=True))
        if usage:
            cert = cert.add_extension(x509.ExtendedKeyUsage([usage]), critical=False)
        if usage == ExtendedKeyUsageOID.SERVER_AUTH:
            cert = cert.add_extension(x509.SubjectAlternativeName([x509.IPAddress(address)]), critical=False)
        cert = cert.sign(issuer[0] if issuer else key, hashes.SHA256())
        return key, cert

    def write_key(path, key):
        save(path, key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))

    def write_cert(path, cert):
        save(path, cert.public_bytes(serialization.Encoding.PEM))

    client_ca, server_ca = issue('trainer-client-ca'), issue('trainer-server-ca')
    for name, pair in (('client-ca', client_ca), ('server-ca', server_ca)):
        write_key(destination / 'authority' / (name + '.key'), pair[0])
        write_cert(destination / 'authority' / (name + '.crt'), pair[1])
    app = issue('trainer-app', client_ca, ExtendedKeyUsageOID.CLIENT_AUTH)
    runner = issue('trainer-runner', server_ca, ExtendedKeyUsageOID.SERVER_AUTH)
    write_key(destination / 'app/app.key', app[0])
    write_cert(destination / 'app/app.crt', app[1])
    write_cert(destination / 'app/server-ca.crt', server_ca[1])
    write_key(destination / 'runner/runner.key', runner[0])
    write_cert(destination / 'runner/runner.crt', runner[1])
    write_cert(destination / 'runner/client-ca.crt', client_ca[1])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('runner_ip')
    args = parser.parse_args()
    create(args.destination, args.runner_ip)
    print('Created TLS files. Leaf certificates expire in 90 days; keep authority keys off both VMs.')
