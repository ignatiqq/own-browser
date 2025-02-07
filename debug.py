def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)

def flat_tree(node, list):
    list.append(node)

    for child in node.children:
        flat_tree(child, list)
        
    return list