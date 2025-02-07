from selectors import TagSelector, DescendantSelector

# рекурсивные функции разбора based парсер
class CSSParser:
    def __init__(self, s):
        self.s = s
        self.sLen = len(self.s)
        self.i = 0
        self.tokens = []

    def isAtEnd(self):
        return self.i >= len(self.s)

    def match(self, symbol):
        return not self.isAtEnd() and self.s[self.i:self.i + len(symbol)] == symbol

    def eat(self, word):
        if self.match(word):
            self.i += len(word)
            return word
        else:
            print('eat() Unexpected token: ', word)
            raise Exception('Unexpected token: ' + symbol)

    def ignore_until(self, chars):
        while not self.isAtEnd():
            if self.s[self.i] in chars:
                return self.s[self.i]
            else:
                self.i += 1
        return None
    
    def readWhileMatching(self, callback):
        start = self.i

        while not self.isAtEnd() and callback():
            self.i += 1
        
        return self.s[start:self.i]

    def body(self):
        pairs = {}
        while not self.isAtEnd() and not self.match('}'):
            # имеем здесь трай кетч
            # для того, чтобы если мы не поддерживаем css фичу пропустить ее
            # или неправильный пользовательский синтакс
            try:
                prop, val = self.pair()
                pairs[prop] = val
                self.whitespace()
                self.literal(';')
                self.whitespace()
            except Exception:
                print("body() Exception", self.i, self.s, 'len: ', len(self.s))
                why = self.ignore_until([';', '}'])

                if why == ";":
                    self.eat(';')
                    self.whtespace()
                else:
                    break
        return pairs

    def pair(self):
        prop = self.word()

        self.whitespace()
        self.literal(':')
        self.whitespace()
        
        val = self.word()
        return prop.casefold(), val

    def isAlphaSymbolic(self):
        return self.s[self.i].isalnum() or self.s[self.i] in "#-.%"

    def word(self):
        text = ''
        
        if not self.isAtEnd():
            text = self.readWhileMatching(self.isAlphaSymbolic)

        return text

    # Функция анализа пробелов увеличивает индекс i после каждого символа пробела
    # Пробелы не имеют смысла, поэтому нет проанализированных данных для возврата
    def whitespace(self):
        while not self.isAtEnd() and self.match(' '):
            self.eat(' ')

    def literal(self, literal):
        if not (not self.isAtEnd() and self.match(literal)):
            raise Exception("Parsing error")
        else:
            self.eat(literal)

    # Parsing CSS selectors from files
    def selector(self):
        out = TagSelector(self.word().casefold())
        self.whitespace()

        # check if we have another selector. it will be "DescendantSelector"
        while not self.isAtEnd() and not self.match('{'):
            tag = self.word()
            descendant = TagSelector(tag.casefold())
             # .rule.depentrule {}
            out = DescendantSelector(out, descendant)
            self.whitespace()
        return out
    
    # parse fully css file
    def parse(self):
        rules = []

        while not self.isAtEnd():
            try:
                self.whitespace()
                selector = self.selector()
                self.literal('{')
                self.whitespace()
                body = self.body()
                self.literal('}')
                rules.append((selector, body))
            except Exception:
                print("Exception parse()")
                why = self.ignore_until(['}'])

                if why == '}':
                    self.literal('}')
                    self.whitespace()
                else:
                    break
        return rules

    