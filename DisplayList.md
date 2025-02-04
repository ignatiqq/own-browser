Изначально до 5 главы display_list представляет собой

``` 
    flush
        /** **/
        self.display_list.append((x, y, word, font))
```

Тоесть был текст со стилями которые мы получали из тегов и добавляли координаты стиль шрифта жирность курсив и тд.

```
if tag == "i":
    self.style ="italic"
elif tag == "b":
    self.weight = "bold"
```

Далее мы будем концептуализировать его как список команд для рисования чего либо на странице:
тоесть "display_list" будет так же содержать текст, но рисовать мы будем не его, а отдеьными "cmds" классами команд

```
cmds = []

class DrawText:
    def __init__(self, x1, y1, text, font):
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
    
class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color
```