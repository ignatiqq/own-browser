import socket
import ssl
import certifi
import os

# Класс реализующий логику запроса 
class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https"]

        if "/" not in url:
            url = url + "/"

        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443

        self.host, url = url.split("/", 1)
        self.path = "/" + url

        # custom user port

    # Первый шаг к загрузке веб-страницы — подключение к хосту. 
    # Операционная система предоставляет для этого функцию, называемую «сокетами». 
    # Когда вы хотите общаться с другими компьютерами 
    # (либо чтобы что-то им сказать, либо чтобы подождать, пока они вам что-то скажут), 
    # вы создаете сокет, а затем этот сокет можно использовать для отправки информации туда и обратно.
    def request(self):
        s = socket.socket(
            # семейство адресатов интернета, есть например еще AF_BLUETOOTH
            family=socket.AF_INET,
            # тип общения стрим - непроизвольный размер ответа / запроса
            type=socket.SOCK_STREAM,
            # протокол описывающий шаги с помощью которых 2 компа установят соединение (7 levels of TCP)
            proto=socket.IPPROTO_TCP
        )
        # https support
        if self.scheme == "https":
            ctx = ssl.create_default_context(cafile=certifi.where())
            ctx.load_verify_locations(
                cafile=os.path.relpath(certifi.where()),
                capath=None,
                cadata=None)
            s = ctx.wrap_socket(s, server_hostname=self.host)
        # подключаемся к другому компьютеру
        s.connect((self.host, self.port))
        # готовим запрос
        request = "GET {} HTTP/1.0\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
        # HTTP/1.1 support for request
        request += "Connection: close\r\n"
        request += "User-Agent: whatever\r\n"
        request += "\r\n"
        s.send(request.encode("utf-8"))

        # читаем ответ = обычная строка utf-8 с пробелами и тд (GET /index.html HTTP/1.0)
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        # читаем статус
        statusline = response.readline()
        version, status, exlanation = statusline.split(" ", 2)
        # заголовки
        response_headers = {}

        while True:
            line = response.readline()
            # заголовки закончились (символ \r\n новой строки обрывает и разделяет разные сущности запроса/ответа)
            if line == "\r\n": break
            # Content-Type:text/html
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        content = response.read()
        s.close()

        return content

    def resolve(self, url):
        # absoulute url (nothing to do)
        if "://" in url: return URL(url)
        if not url.startsWith('/'):
            dir, _ = self.path.rsplit("/", 1)
            while url.startswith("../"):
                _, url = url.split("/", 1)
                if "/" in dir:
                    dir, _ = dir.rsplit("/", 1)
            url = dir + "/" + url
        if url.startswith("//"):
            return URL(self.scheme + ":" + url)
        else:
            return URL(self.scheme + "://" + self.host + ":" + str(self.port) + url)