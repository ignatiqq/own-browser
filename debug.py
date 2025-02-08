def print_node(node, indent=0): 
    print(" " * indent, node)

def print_node_style(node, indent=0):
    print(" " * indent, 'node: ', node, node.style)

def print_tree(node, callback, indent=0):
    callback(node, indent)
    for child in node.children:
        print_tree(child, callback, indent + 2)

def flat_tree(node, list):
    list.append(node)

    for child in node.children:
        flat_tree(child, list)
        
    return list