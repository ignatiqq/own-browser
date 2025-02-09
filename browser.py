from style import CSSParser, style
from drawers import DrawText, DrawRect
from url import URL
from nodes import Text, Element
from debug import print_tree, print_node, print_node_style, flat_tree
from selectors import cascade_priority
from htmlParser import HTMLParser
from layout import DocumentLayout


# графический инструментарий для упрощения шагов рисования
import tkinter
import tkinter.font as tkfont

HSTEP, VSTEP = 30, 18
WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100

# Функция получающая объект макета и извлекающая из него дисплей лист
# соединяет с массивом дислей лист из 2 аргумента и рисует их
def paint_tree(layout_object, display_list):
    display_list.extend(layout_object.paint())

    for child in layout_object.children:
        paint_tree(child, display_list)

# дефолтная таблица стилей для нашего браузера
DEFAULT_STYLE_SHEET = CSSParser(open("userAgentStyles.css").read()).parse()

# UI нашнего браузера 
class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
            bg="white"
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
        links = [node.attributes["href"]
                 for node in flat_tree(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and node.attributes.get("rel") == "stylesheet"
                 and "href" in node.attributes]
        for link in links:
            if 'fonts.googleapis.com' in link: continue
            style_url = url.resolve(link)
            try:
                body = style_url.request()
            except:
                print('Error while fetch data: ', link)
                continue
            
            rules.extend(CSSParser(body).parse())

        style(self.nodes, sorted(rules, key=cascade_priority))
        # print_tree(self.nodes, print_node_style)

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
