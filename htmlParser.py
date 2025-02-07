from nodes import Text, Element

# Parser things (lexing)

SELF_CLOSING_TAGS = [
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
]

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
                # remove all "" and ''
                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1:-1]

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