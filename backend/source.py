"""Fetch public pages with DNS pinning and a fresh public-IP check on every redirect."""
import http.client
import ipaddress
import re
import socket
import ssl
import time
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit


class SourceError(Exception):
    pass


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []
        self.main = []
        self.article = []
        self.main_depth = self.article_depth = 0
        self.code = None
        self.code_language = ''

    def append(self, text):
        self.parts.append(text)
        if self.main_depth:
            self.main.append(text)
        if self.article_depth:
            self.article.append(text)

    def text(self):
        for parts in (self.article, self.main, self.parts):
            text = ''.join(parts).strip()
            if text:
                return text
        return ''

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'svg', 'nav', 'footer'):
            self.hidden += 1
        if self.hidden:
            return
        if tag == 'main':
            self.main_depth += 1
        if tag == 'article':
            self.article_depth += 1
        if tag == 'pre':
            self.code = []
            self.code_language = ''
        if self.code is not None:
            for name, value in attrs:
                if name == 'class':
                    match = re.search(r'(?:language|lang)-([\w+#.-]+)', value or '')
                    if match:
                        self.code_language = match[1]
            if tag == 'br':
                self.code.append('\n')
            return
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.append('\n\n' + '#' * int(tag[1]) + ' ')
        elif tag in ('p', 'div', 'section', 'li', 'br', 'tr'):
            self.append('\n')
        elif tag == 'code':
            self.append('`')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'svg', 'nav', 'footer'):
            self.hidden = max(0, self.hidden - 1)
            return
        if self.hidden:
            return
        if tag == 'pre' and self.code is not None:
            code = ''.join(self.code).strip('\n')
            fence = '`' * max(3, 1 + max((len(m) for m in re.findall(r'`+', code)), default=0))
            self.append('\n\n' + fence + self.code_language + '\n' + code + '\n' + fence + '\n\n')
            self.code = None
        elif self.code is not None:
            return
        elif tag == 'code':
            self.append('`')
        elif tag in ('p', 'div', 'section', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.append('\n')
        if tag == 'article':
            self.article_depth = max(0, self.article_depth - 1)
        if tag == 'main':
            self.main_depth = max(0, self.main_depth - 1)

    def handle_data(self, text):
        if not self.hidden:
            if self.code is not None:
                self.code.append(text)
            else:
                self.append(re.sub(r'\s+', ' ', text))


def prepare(text):
    """Keep code blocks and their surrounding sections, without duplicating tokens."""
    lines = text.splitlines(keepends=True)
    document, examples, headings = [], [], []
    def add_example(code, language, original):
        if code.strip() and len(code) <= 24000:
            example_id = f's{len(examples) + 1}'
            examples.append({'id': example_id, 'section': ' / '.join(h for _, h in headings),
                             'language': language, 'code': code})
            document.append(f'\n[코드 예제 {example_id}]\n')
        else:
            document.extend(original)

    index = 0
    while index < len(lines):
        line = lines[index]
        heading = re.match(r'^ {0,3}(#{1,6})\s+(.+)', line)
        if heading:
            depth = len(heading[1])
            headings = [(d, h) for d, h in headings if d < depth] + [(depth, heading[2].strip())]
        opening = re.match(r'^ {0,3}(`{3,}|~{3,})([^\r\n]*)\r?\n?$', line)
        if not opening and line.startswith(('    ', '\t')) and (index == 0 or not lines[index - 1].strip()):
            end, code = index, []
            while end < len(lines) and (not lines[end].strip() or lines[end].startswith(('    ', '\t'))):
                code.append(lines[end][4:] if lines[end].startswith('    ') else lines[end].removeprefix('\t'))
                end += 1
            add_example(''.join(code), '', lines[index:end])
            index = end
            continue
        if not opening:
            document.append(line)
            index += 1
            continue
        end = index + 1
        closing = r'^ {0,3}' + re.escape(opening[1][0]) + '{' + str(len(opening[1])) + r',}\s*$'
        while end < len(lines) and not re.match(closing, lines[end]):
            end += 1
        code = ''.join(lines[index + 1:end])
        add_example(code, opening[2].strip().split(' ')[0][:80], lines[index:min(end + 1, len(lines))])
        index = end + 1
    return ''.join(document), examples


def public_address(host, port):
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise SourceError('공개 인터넷 문서 주소만 사용할 수 있습니다.')
    return addresses[0][4][0]


def fetch_bytes(url, content_types=('text/html', 'text/plain', 'text/markdown'), max_bytes=400000):
    deadline = time.monotonic() + 20
    try:
        for _ in range(4):
            parts = urlsplit(url)
            if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password or len(url) > 2000:
                raise SourceError('올바른 HTTP(S) 문서 주소를 입력해주세요.')
            port = parts.port or (443 if parts.scheme == 'https' else 80)
            if port not in (80, 443):
                raise SourceError('표준 웹 포트의 문서만 가져올 수 있습니다.')
            address = public_address(parts.hostname, port)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise SourceError('문서 가져오기 시간이 초과되었습니다.')
            connection = http.client.HTTPConnection(parts.hostname, port, timeout=min(8, remaining))
            try:
                connection.sock = socket.create_connection((address, port), timeout=min(8, remaining))
                if parts.scheme == 'https':
                    connection.sock = ssl.create_default_context().wrap_socket(connection.sock, server_hostname=parts.hostname)
                connection.request('GET', (parts.path or '/') + ('?' + parts.query if parts.query else ''),
                    headers={'User-Agent': 'CodeTrainer/0.1', 'Accept': ','.join(content_types), 'Accept-Encoding': 'identity'})
                response = connection.getresponse()
                if response.status in (301, 302, 303, 307, 308):
                    location = response.getheader('Location')
                    if not location:
                        raise SourceError('문서의 이동 주소를 확인할 수 없습니다.')
                    url = urljoin(url, location)
                    continue
                if response.status != 200 or response.getheader('Content-Encoding', 'identity') != 'identity':
                    raise SourceError('문서를 가져오지 못했습니다. 본문을 붙여넣어주세요.')
                content_type = response.getheader('Content-Type', '').split(';')[0]
                if content_type not in content_types:
                    raise SourceError('텍스트 또는 HTML 문서를 사용해주세요.')
                body = bytearray()
                while chunk := response.read1(8192):
                    body.extend(chunk)
                    if len(body) > max_bytes or time.monotonic() > deadline:
                        raise SourceError('문서가 너무 크거나 응답이 늦습니다. 필요한 본문을 붙여넣어주세요.')
                return bytes(body), content_type
            finally:
                connection.close()
        raise SourceError('문서의 이동 횟수가 너무 많습니다. 본문을 붙여넣어주세요.')
    except (OSError, ValueError, http.client.HTTPException):
        raise SourceError('주소에 접근하지 못했습니다. 본문을 붙여넣어주세요.') from None


def fetch(url):
    body, content_type = fetch_bytes(url)
    text = body.decode('utf-8', errors='replace')
    if content_type == 'text/html':
        parser = TextParser()
        parser.feed(text)
        text = parser.text()
    if len(text) > 60000 or len(text.strip()) < 20:
        raise SourceError('분석할 본문 범위를 20~60,000자로 붙여넣어주세요.')
    return text
