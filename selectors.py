from nodes import Element

# TagSelector for selectors like this: 'a, pre, section'
class TagSelector:
    def __init__(self, tag):
        self.tag = tag
        # specifity
        self.priority = 1
    
    def matches(self, node):
        return isinstance(node, Element) and self.tag == node.tag

# Combination of TagSelector's for selectors like this: 'section a, div code'
class DescendantSelector:
    def __init__(self, ancestor, descendant):
        # Selector
        self.ancestor = ancestor
        # Selector
        self.descendant = descendant
        # priority sum of tags/selectors
        self.priority = ancestor.priority + descendant.priority
    
    def matches(self, node):
        if not self.descendant.matches(node): return False

        while node.parent:
            if self.ancestor.matches(node.parent): return True
            node = node.parent
        
        return False

def cascade_priority(rule):
    selector, body = rule
    return selector.priority