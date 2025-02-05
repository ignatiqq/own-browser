# рекурсивные функции разбора based парсер
class CSSParser:
    def __init__(self, s):
        self.s = s
        self.sLen = len(self.s)
        self.i = 0
        self.tokens = []

    def isAtEnd(self):
        return self.i === self.sLen

    def match(self, symbol):
        return self.s[self.i:len(symbol)] == symbol

    def eat(self, word):
        if self.match(word):
            self.i += len(word)
            return word
        else:
            raise Exception('Unexpected token: ' + symbol)

    def skipUntil(self, symbol):
        while not self.isAtEnd():
            if self.match(symbol):
                return symbol
            else:
                self.i += 1
        return None

    def body(self):
        pairs = {}

        while not self.isAtEnd():
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
                # пропускаем ошибочный код
                char = self.skipUntil(';')

                if self.match(';'):
                    self.eat(';')
                else:
                    break
        return pairs

    def pair(self):
        prop = self.word()

        self.whitespace()
        self.literal(":")
        self.whitespace()

        val = self.word()
        return prop.casefold(), val

    def word(self):
        text = ''

        while !not self.isAtEnd():
            if self.s[self.i].isalnum() or self.s[self.i] in "#-.%":
                text += self.s[self.i]
            else:
                break

        print(text)
        self.eat(text)

        return text


    # Функция анализа пробелов увеличивает индекс i после каждого символа пробела
    # Пробелы не имеют смысла, поэтому нет проанализированных данных для возврата
    def whitespace(self):
        while not self.isAtEnd()  and self.s[self.i].isspace():
            self.i += 1

    def literal(self, literal):
        if literal == ":": this.eat(":")
        elif literal == ";": this.eat(";")

    