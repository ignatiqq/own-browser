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

BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]

# Классы стилизаций для display_list
class DrawText:
    def __init__(self, x1, y1, text, font):
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
        self.bottom = y1 + font.metrics("linespace")

    def execute(self, scroll, canvas):
        canvas.create_text(
            self.left, self.top - scroll,
            text=self.text,
            font=self.font,
            anchor='nw')

class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color

    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            # no border
            width=0,
            fill=self.color
        )

class Text:
    def __init__(self, text, parent):
        self.text = text
        # для согласования классов элементов в парсере
        self.children = []
        self.parent = parent
    
    def __repr__(self):
        return repr(self.text)

# Класс для тегов
# Element, а не тег, так как 1 тег это по сути открывающий и закрывающий
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
        # исходный анализируемый код
        self.body = body
        # здесь храним открытые, но не успевшие закрыться на данный момент теги
        self.unfinished = []
        self.HEAD_TAGS = [
            "base", "basefont", "bgsound", "noscript",
            "link", "meta", "title", "style", "script",
        ]

    def add_text(self, text):
        # пропускаем строку состояющую из пробелов
        # например "/n" после пропуска <!doctype> на странице
        if text.isspace(): return
        self.implicit_tags(None)

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
            # по порядку открытые и закрытые теги
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
            # как эти теги будут влиять на разметку?
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()
    
    # функция которая добавляет пропущенные теги разработчиком
    # Этот валидатор вызывается в функция парсинга перед обработкой элемента
    def implicit_tags(self, tag):
        while True:
            # мапка анфинишед нод
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

# Функция получающая объект макета и извлекающая из него дисплей лист
# соединяет с массивом дислей лист из 2 аргумента и рисует их
def paint_tree(layout_object, display_list):
    display_list.extend(layout_object.paint())

    for child in layout_object.children:
        paint_tree(child, display_list)

def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)

# Браузерный лейаут (макет) / Вычисление позиции на станице

# Принимает на вход дерево элементов которые мы спарсили и добавляем к ним свойства Макета (Layout)

# оутпут называется display list это стандартное название в браузерах
# ПОДРОБНЕЕ - https://browser.engineering/layout.html#the-layout-tree
class BlockLayout:
    def __init__(self, tokens, parent, previous):
        # tree props
        # дефолтные пропсы для структуры дерева
        self.node = tokens
        self.parent = parent
        self.previous = previous
        self.children = []
        # self properties
        # display_list = только слова с их стилями и координатами
        # Одна единица дисплей лист это набор слов (объектов), стилизованных тегами имеющие разные аттрибуты
        self.display_list = [] 
        self.size = 12
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.font = tkfont.Font()
        self.line = []
        self.flush()
        # page position
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        # поле нужное для вычисления x позиций текста на странице

    def layout(self):
        self.x = self.parent.x
        self.width = self.parent.width
        
        # Вертикальное положение макета объекта зависит от того есть ли у элемента сиблинг
        # чтобы выровнять по нему
        if self.previous:
            # self.y = начало пред блока + его высота
            self.y = self.previous.y + self.previous.height
        # если нет сиблинга берем "y" родителя
        else:
            self.y = self.parent.y

        mode = self.layout_mode()

        if mode == "block":
            self.layout_intermediate()
        else:
            # для текст ноды его координаты всегда относительны его самого
            self.cursor_x = 0
            self.cursor_y = 0
            self.weight = "normal"
            self.style = "roman"
            self.size = 12

            self.line = []
            self.recurse(self.node)
            self.flush()

        # Dom iterations
        for child in self.children:
            child.layout()

        if mode == "block":
            # Каждый блок = родитель
            # минимальная высота блока родителя это вся высота всех его дочерних элементов
            self.height = sum([child.height for child in self.children])
        else:
            # высота текста это высота родительского элемента
            self.height = self.cursor_y


    # Сбрасывание оставшихся стилей и координатов текста до нулевых для след строки
    # 1. необходимо выровнять слова по базовой линии (см. рисунок 5);
    # 2. он должен добавить все эти слова в список отображения; и
    # 3. необходимо обновить поля cursor_xи cursor_y .
    def flush(self):
        if not self.line: return
        # координаты + выравниваем по линии (вычисление самого высокого слова в линии)
        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        
        # добавляем текст в дисплей лист
        for rel_x, word, font in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))
        
        # обновляем поля x,y
        self.cursor_x = 0
        self.line = []
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

    def processWord(self, word):
        # для одного и того же начертания не создаем инстансы шрифтов и лейблов (КЕШ)
        font = get_font(size=self.size, weight=self.weight, style=self.style)
        w = font.measure(word)

        if self.cursor_x + w > self.width:
            self.flush()

        # Буфер где слова удерживаются прежде чем мы будем их рисовать
        self.line.append((self.cursor_x, word, font))
        # двигаем текст по х вправо
        self.cursor_x += w + font.measure(' ')
        # делаем перенос строки когда текс по x ушел за окно

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

    # Функция отвечает за тип элеммента inline или block элемент сейас обрабатывается
    # определит что мы обрабатываем <p> | <h1> блоки и тд. Либо <big>, <small> TextNode инлайн элементы.
    def layout_mode(self):
        if isinstance(self.node, Text):
            return "inline"
        # Если тип ноды Element (против Text) и чилдрены элемента блочные элементы
        elif any([isinstance(child, Element) and child.tag in BLOCK_ELEMENTS for child in self.node.children]):
            return "block"
        elif self.node.children:
            return "inline"
        else:
            return "block"

    # построение блоков вертикально
    # манипулирование деревьями:
    # Макета (Layout): self, previous, next
    # DOM (Parsed Tokens): self.node, child
    # self.children = Layout "(так как next это инстанс BlockLayout)"
    def layout_intermediate(self):
        # собираем сиблингов для BlockLayout(,,previous)
        previous = None
        # dfs
        for child in self.node.children:
            # Этот код содержит обработку как (output HTMLParser (html parser tree === HTML TREE === DOM))
            # Так и Layout дерево с теми же полями node, chilren, previous
            # Они отличаются 
            # child = DOM
            # self.node = DOM
            # next, self, previous = LayoutTREE
            next = BlockLayout(child, self, previous)
            self.children.append(next)
            previous = next
            
    # Обработка ТЕКСТОВЫХ элементов или их стилизаций <b>, <small> ...
    def recurse(self, tree):
        if isinstance(tree, Text):
            for word in tree.text.split():
                self.processWord(word)
        else:
            self.open_tag(tree.tag)
            for child in tree.children:
                self.recurse(child)
            self.close_tag(tree.tag)

    def paint(self):
        cmds = []

        # красим все pre блоки в серый
        if isinstance(self.node, Element) and self.node.tag == "pre":
            # определяем конечные точки по x,y учитывая длину и высоту
            # чтобы получить квадратные координаты
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, "gray")
            cmds.append(rect);

        # Класс для рисования текста
        if self.layout_mode() == "inline":
            for x, y, word, font in self.display_list:
                cmds.append(DrawText(x, y, word, font))

        return cmds


# Родительский (корневой элемент для Layout) document
class DocumentLayout:
    def __init__(self, node):
        # DOM
        self.node = node
        self.parent = None
        self.previos = None
        # Layout (так как в self.children кладем инстанс класса block layout)
        self.children = []

    def layout(self):
        child = BlockLayout(self.node, self, None)
        self.children.append(child)

        self.width = WIDTH - 2*HSTEP
        self.x = HSTEP
        self.y = VSTEP
        child.layout()
        self.height = child.height

    def paint(self):
        return []


# UI нашнего браузера 
class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        self.canvas.pack()
        self.windowWidth = WIDTH;
        self.windowHeight = HEIGHT;
        self.scroll = 0
        # Tk позволяет вам привязать функцию к клавише, которая инструктирует Tk вызывать эту функцию при нажатии клавиши.
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        # self.window.bind("<Configure>", self.resize)
        SCROLL_STEP = 100

    # функция скрола
    def scrolldown(self, e):
        # прибавляем оффсет скролу, от которого зависит отрисовка в .draw()
        max_y = max(self.document.height + 2 * VSTEP - HEIGHT, 0)
        # если конец странице меньше - дальше не листаем
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
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
        for cmd in self.display_list:
            # $оптимизация: не рисуем того, чего нет на экране
            if cmd.top > self.scroll + self.windowHeight: continue
            if cmd.bottom < self.scroll: continue

            cmd.execute(self.scroll, self.canvas)

    # метод рисующий на холсте
    def load(self, url):
        body = url.request()
        self.nodes = HTMLParser(body).parse()
        # self.cachedToken = self.nodes;
        # self.document = object with global property ad display list now
        self.document = DocumentLayout(self.nodes)
        self.document.layout();
        # merge created LAYOUT OBJECT display list
        self.display_list = []
        paint_tree(self.document, self.display_list)
        self.draw()

if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()
