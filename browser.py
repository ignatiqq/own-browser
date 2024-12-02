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


# графический инструментарий для упрощения шагов рисования
import tkinter
import tkinter.font as tkfont

window = tkinter.Tk()
bi_times = tkfont.Font(
    family="Times New Roman",
    size=16,
)

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 30, 18
SCROLL_STEP = 100
# кеш для слов при лейауте странички и определния позиции слов
FONTS = {}
# функция кеширования
def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]

# Parser things (lexing)

SELF_CLOSING_TAGS = [
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
]

class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent
    
    def __repr__(self):
        return repr(self.text)

class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.children = []
        self.parent = parent
        self.attributes = attributes

    def __repr__(self):
        return "<" + repr(self.tag) + ">"

class HTMLParser:
    def __init__(self, body):
        self.body = body
        self.unfinished = []
        self.HEAD_TAGS = [
            "base", "basefont", "bgsound", "noscript",
            "link", "meta", "title", "style", "script",
        ]

    def add_text(self, text):
        # doctype <!-- --> and etc
        if text.isspace(): return
        self.implicit_tags(None)
        # берем последний элемент незакрытого тега из стека
        # и кладем элемент текста в "parent" тег
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    def get_attributes(self, text):
        #     # ...
        # if len(value) > 2 and value[0] in ["'", "\""]:
        #     value = value[1:-1]
        # # ...
        parts = text.split()
        tag = parts[0].casefold()
        attributes = {}
        for attrpair in parts[1:]:
            # key=val
            if "=" in attrpair:
                key, value = attrpair.split("=", 1)
                attributes[key.casefold()] = value
            # disabled
            else:
                attributes[attrpair.casefold()] = ""
        return tag, attributes

    def add_tag(self, tag):
        tag, attributes = self.get_attributes(tag)
        # doctype <!-- --> and etc
        if tag.startswith("!"): return
        self.implicit_tags(tag)
        # extract all attrs and process self closing tags
        # закрывающий тег, тоесть должны вытащить предыдущий
        if tag.startswith("/"):
            #  нет незавершенного узла, к которому можно было бы его добавить
            if len(self.unfinished) == 1: return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        # открывающий тег просто кладем в стек
        elif tag in SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)

    def finish(self):
        if not self.unfinished:
            self.implicit_tags(None)
        # так как html парсер "щадящий"
        # мы закроем все теги, которые забыл проставить пользователь сами
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()
    
    # функция которая добавляет пропущенные теги разработчиком
    # Этот валидатор вызывается в функция парсинга перед обработкой элемента
    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            # неявный html (если последний тег и нет html)
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            # проверяем является ли потомок html валидным элементом(если последний тег и нет html)
            # (если предпоследний тег (до html) и нет body head или /html)
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
                # если встретили <link> <meta> и тд
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            # если в хеде нашли неваидный тег (закрываем автоматически как и в реальных браузерах)
            elif open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            else:
                break

    def parse(self):
        text = ""
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                # flush
                if text: self.add_text(text)
                text = ""
            elif c == ">":
                in_tag = False
                self.add_tag(text)
                text = ""
            else:
                # may be text or tag
                text += c
        if not in_tag and text:
            self.add_text(text)
        return self.finish()

def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)

# Браузерный лейаут (макет) / Вычисление позиции на станице
# оутпут называется display list это стандартное название в браузерах
class Layout:
    def __init__(self, tokens, width):
        self.display_list = []
        self.size = 12
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.width = width
        self.weight = "normal"
        self.style = "roman"
        self.font = tkfont.Font()
        self.line = []
        self.startLayout(tokens)
        self.flush()
        # поле нужное для вычисления x позиций текста на странице

    def startLayout(self, tokens):
        self.recurse(tokens)

    def flush(self):
        if not self.line: return
        metrics = [self.font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        
        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))
        
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = HSTEP
        self.line = []

    def processWord(self, word):
        font = get_font(size=self.size, weight=self.weight, style=self.style)
        w = font.measure(word)
        self.line.append((self.cursor_x, word, font))
        # двигаем текст по х вправо
        self.cursor_x += w + font.measure(' ')
        # делаем перенос строки когда текс по x ушел за окно
        if self.cursor_x + w > self.width - HSTEP:
            self.flush()

    def open_tag(self, tag):
        if tag == "i":
            self.style ="italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "big":
            self.size += 4
        elif tag == "br":
            self.flush()
    # начертание текста в заивимости от тега <b><i>bold italic</i></b>, <b>bold</b>
    def close_tag(self, tag):
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "p":
            self.flush()
            self.cursor_y += VSTEP
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4

    def recurse(self, tree):
        if isinstance(tree, Text):
            for word in tree.text.split():
                self.processWord(word)
        else:
            self.open_tag(tree.tag)
            for child in tree.children:
                self.recurse(child)
            self.close_tag(tree.tag)

# UI нашнего браузера 
class Browser:
    def __init__(self):
        self.window = window
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        self.windowWidth = WIDTH;
        self.windowHeight = HEIGHT;
        self.canvas.pack(fill=tkinter.BOTH, expand=True)
        self.scroll = 0
        # Tk позволяет вам привязать функцию к клавише, которая инструктирует Tk вызывать эту функцию при нажатии клавиши.
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<Configure>", self.resize)
        SCROLL_STEP = 100

    # очень неоптимизированный ресайз
    def resize(self, e):
        self.windowWith = e.width
        self.windowHeight = e.height

        self.display_list = Layout(self.cachedToken, self.windowWith).display_list
        self.draw()

    # функция скрола
    def scrolldown(self, e):
        # прибавляем оффсет скролу, от которого зависит отрисовка в .draw()
        self.scroll += SCROLL_STEP
        self.draw()

         # функция скрола
    def scrollup(self, e):
        # прибавляем оффсет скролу, от которого зависит отрисовка в .draw()
        if (self.scroll - SCROLL_STEP) >= 0:
            self.scroll = max(0, self.scroll - SCROLL_STEP)
            self.draw()
    # браузерная отрисовка после макета (лейаута) по пикселям рисуем контент
    def draw(self):
        # чистим все содержимое перед слудеющей отрисовкой чтоб не было дубля на странице (кляксы)
        self.canvas.delete("all")
        for x, y, c, font in self.display_list:
            # $оптимизация: не рисуем того, чего нет на экране
            if y > self.scroll + self.windowHeight: continue
            if y + VSTEP < self.scroll: continue
            # рисуем в tkinter + поддержка скрола
            self.canvas.create_text(x, y - self.scroll, text=c, font=font)

    # метод рисующий на холсте
    def load(self, url):
        body = url.request()
        self.nodes = HTMLParser(body).parse()
        self.cachedToken = self.nodes;
        self.display_list = Layout(self.nodes, self.windowWidth).display_list
        self.draw()

if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()
