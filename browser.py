from CSSParser import CSSParser
from drawers import DrawText, DrawRect
from url import URL
from nodes import Text, Element
from debug import print_tree
from htmlParser import HTMLParser


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

BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]

def style(node, rules):
    node.style = {}

    for selector, body in rules:
        if not selector.matches(node): continue
        for prop, value in body.items():
            node.style[prop] = value

    # style переопределяет стили из СSS
    if isinstance(node, Element) and "style" in node.attributes:
        pairs = CSSParser(node.attributes["style"]).body()
        for prop, value in pairs.items():
            node.style[prop] = value
            
    for child in node.children:
        style(child, rules)


# Функция получающая объект макета и извлекающая из него дисплей лист
# соединяет с массивом дислей лист из 2 аргумента и рисует их
def paint_tree(layout_object, display_list):
    display_list.extend(layout_object.paint())

    for child in layout_object.children:
        paint_tree(child, display_list)

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
    # 4. Начнет с новой строки
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
        if isinstance(self.node, Element):
            bgcolor = self.node.style.get("background-color", "transparent")
            # определяем конечные точки по x,y учитывая длину и высоту
            # чтобы получить квадратные координаты
            if bgcolor != "transparent":
                x2, y2 = self.x + self.width, self.y + self.height
                rect = DrawRect(self.x, self.y, x2, y2, bgcolor)
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

# дефолтная таблица стилей для нашего браузера
DEFAULT_STYLE_SHEET = CSSParser(open("userAgentStyles.css").read()).parse()

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
        # REQUEST
        body = url.request()
        # LEXING
        self.nodes = HTMLParser(body).parse()
        # CSS
        rules = DEFAULT_STYLE_SHEET.copy()
        style(self.nodes, rules)
        # LAYOUTING
        self.document = DocumentLayout(self.nodes)
        self.document.layout();
        self.display_list = []
        paint_tree(self.document, self.display_list)
        # UI DRAWING
        self.draw()

if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()
