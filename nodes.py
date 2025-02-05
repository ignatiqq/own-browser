
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