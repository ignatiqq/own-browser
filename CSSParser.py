# рекурсивные функции разбора based парсер
class CSSParser:
    def __init__(self, s):
        self.s = s
        self.sLen = len(self.s)
        self.i = 0
        self.tokens = []

    def isAtEnd(self):
        return self.i == self.sLen

    def match(self, symbol):
        return self.s[self.i:self.i + len(symbol)] == symbol

    def eat(self, word):
        if self.match(word):
            self.i += len(word)
            return word
        else:
            print('Unexpected token: ', word)
            raise Exception('Unexpected token: ' + symbol)

    def skipUntil(self, symbol):
        while not self.isAtEnd():
            if self.match(symbol):
                return symbol
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
        while not self.isAtEnd():
            # имеем здесь трай кетч
            # для того, чтобы если мы не поддерживаем css фичу пропустить ее
            # или неправильный пользовательский синтакс
            try:
                prop, val = self.pair()
                print(prop, val)
                pairs[prop] = val
                self.whitespace()
                self.literal()
                self.whitespace()
            except Exception:
                # пропускаем ошибочный код
                char = self.skipUntil(';')
                print("Exception")

                if self.match(';'):
                    self.eat(';')
                else:
                    break
        return pairs

    def pair(self):
        prop = self.word()

        self.whitespace()
        self.literal()
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

    def literal(self):
        if self.match(':'): self.eat(":")
        elif self.match(';'): self.eat(";")

    