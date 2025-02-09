import tkinter
import tkinter.font as tkfont
from nodes import Text, Element
from drawers import DrawText, DrawRect

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 30, 18

BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]

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
        # BlockLayout | LineLayout -> TextLayout
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
            self.new_line()
            self.recurse(self.node)

        # Dom iterations
        for child in self.children:
            child.layout()

        # Каждый блок = родитель
        # минимальная высота блока родителя это вся высота всех его дочерних элементов
        # self.height = sum([child.height for child in self.children])

        # высота текста это высота родительского элемента
        self.height = sum([child.height for child in self.children])


    # Сбрасывание оставшихся стилей и координатов текста до нулевых для след строки
    # 1. необходимо выровнять слова по базовой линии (см. рисунок 5);
    # 2. он должен добавить все эти слова в список отображения; и
    # 3. необходимо обновить поля cursor_xи cursor_y .
    # 4. Начнет с новой строки
    def flush(self):
        if not self.line: return
        # координаты + выравниваем по линии (вычисление самого высокого слова в линии)
        metrics = [font.metrics() for x, word, font, color in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        
        # добавляем текст в дисплей лист
        for rel_x, word, font, color in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font, color))
        
        # обновляем поля x,y
        self.cursor_x = 0
        self.line = []
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

    def processWord(self, node, word):
        color = node.style["color"]
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)

        font = get_font(size, weight, style)
        w = font.measure(word)
        
        if self.cursor_x + w > self.width:
            self.new_line()

        # берем последнюю линию в тексте (создается в new_line)
        line = self.children[-1]
        # если в линии есть слова (изначально пустая = None)
        previous_word = line.children[-1] if line.children else None
        # создаем текст с предыдущим словом либо None
        text = TextLayout(node, word, line, previous_word)
        # кладем в линию текст
        line.children.append(text)

        # двигаем текст по х вправо
        self.cursor_x += w + font.measure(' ')

    def new_line(self):
        # line always starts with 0 x
        self.cursor_x = 0
        # создаем либо берем последнюю линию для сиблинга
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)

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
                self.processWord(tree, word)
        else:
            if tree.tag == "br":
                self.flush()
            for child in tree.children:
                self.recurse(child)

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
        # если лейаут класс инлайновый то можем покрасить текст
        if self.layout_mode() == "inline":
            for x, y, word, font, color in self.display_list:
                cmds.append(DrawText(x, y, word, font, color))

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

class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []

    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        for word in self.children:
            word.layout()

        if not self.children:
            self.height = 0
            return

        # Вычисления позиции текста и присваиванием y TextLayout на основе всего текста в линии
        max_ascent = max([word.font.metrics("ascent") for word in self.children])
        baseline = self.y + 1.25 * max_ascent
        for word in self.children:
            word.y = baseline - word.font.metrics("ascent")
        max_descent = max([word.font.metrics("descent") for word in self.children])
        self.height = 1.25 * (max_ascent + max_descent)

    # красить нечего, класс просто содержит children[TextLayout]
    def paint(self):
        return []

class TextLayout:
    def __init__(self, node, word, parent, previous):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous
    
    # здесь нет кода для вычисления yпозиции. Вертикальная позиция одного слова зависит от других слов в той же строке,
    # поэтому мы вычислим эту y позицию внутри LineLayout метода layout.
    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = get_font(size, weight, style)

        self.width = self.font.measure(self.word)

        if self.previous:
            space = self.previous.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = self.font.metrics("linespace")
    
    def paint(self):
        color = self.node.style["color"]
        return [DrawText(self.x, self.y, self.word, self.font, color)]