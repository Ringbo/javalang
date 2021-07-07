import pickle

import six

typePriority = {
    'StatementExpression': 1,
    'LocalVariableDeclaration': 1,
    'AssertStatement': 1,
    'WhileStatement': 1,
    'IfStatement': 1,
    'TryStatement': 1,
    'ThrowStatement': 1,
    'SwitchStatement': 1,
    'SwitchStatementCase': 1,
    'ReturnStatement': 1,
    'DoStatement': 1,
    'ForStatement': 1,
    'FieldDeclaration': 1,
    'SynchronizedStatement':1
}


class MetaNode(type):
    def __new__(mcs, name, bases, dict):
        attrs = list(dict['attrs'])
        dict['attrs'] = list()

        for base in bases:
            if hasattr(base, 'attrs'):
                dict['attrs'].extend(base.attrs)

        dict['attrs'].extend(attrs)

        return type.__new__(mcs, name, bases, dict)


@six.add_metaclass(MetaNode)
class Node(object):
    attrs = ()

    def __init__(self, **kwargs):
        values = kwargs.copy()
        self.tokens = set()
        for attr_name in self.attrs:
            value = values.pop(attr_name, None)
            setattr(self, attr_name, value)

        if values:
            raise ValueError('Extraneous arguments')

    def __equals__(self, other):
        if type(other) is not type(self):
            return False

        for attr in self.attrs:
            if getattr(other, attr) != getattr(self, attr):
                return False

        return True


    def __repr__(self):
        attr_values = []
        for attr in sorted(self.attrs):
            attr_values.append('%s=%s' % (attr, getattr(self, attr).__repr__()))
        return '%s(%s)' % (type(self).__name__, ', '.join(attr_values))

    # def __toToken__(self):
    #     attr_values = []
    #     for attr in sorted(self.attrs):
    #         if not (attr == "name" or attr == "value" or attr == "types" or attr == "member"): continue
    #         if getattr(self,'position') is None:
    #             print("")
    #         if hasattr(self,'_tag'):
    #             print("")
    #         if attr == "types":
    #             attr_values.append('%s=%s' % (''.join(getattr(self, attr)),getattr(self,'position')))
    #         else:
    #             attr_values.append('%s=%s' % (getattr(self, attr).__repr__(),getattr(self,'position')))
    #     return ', '.join(attr_values)


    def __iter__(self):
        return walk_tree(self)

    def filter(self, pattern):
        for path, node in self:
            if ((isinstance(pattern, type) and isinstance(node, pattern)) or
                (node == pattern)):
                yield path, node

    @property
    def children(self):
        return [getattr(self, attr_name) for attr_name in self.attrs]
    
    @property
    def position(self):
        if hasattr(self, "_position"):
            return self._position

def walk_tree(root):
    children = None

    if isinstance(root, Node):
        yield (), root
        children = root.children
    else:
        children = root

    for child in children:
        if isinstance(child, (Node, list, tuple)):
            for path, node in walk_tree(child):
                yield (root,) + path, node


def walk_tree_2(root, pre_type):
    children = None
    if isinstance(root, Node):
        if type(root).__name__ in typePriority:
            curType = type(root).__name__
        else:
            curType = pre_type
        if hasattr(root,'_token') and curType is not None:
            if isinstance(root._token,list):
                for _token in root._token:
                    _token.stmt_type = curType
                    yield _token
            else:
                root._token.stmt_type = curType
                if hasattr(root,'modifiers') and root.modifiers:
                    root._token.value = "_".join(list(root.modifiers) + [root._token.value])
                yield root._token
        else:
            pass
            # print("",end='')
        children = root.children
    else:
        children = root
    for child in children:
        if isinstance(child, (Node, list, tuple)):
            if type(child).__name__ in typePriority:
                curType = type(child).__name__
            else:
                curType = pre_type
            for node in walk_tree_2(child, curType):
                    yield node

def walk_tree_3(root, pre_type,curTypePriority=None):
    if curTypePriority is None:
        curTypePriority = typePriority
    children = None
    if isinstance(root, Node):
        if type(root).__name__ in curTypePriority:
            curType = type(root).__name__
            pre_type = curType
        else:
            curType = pre_type
        if hasattr(root,'position'):
            # if hasattr(root,'curType') and root.curType is not None:
            #     print("")
            root.curType = curType
            yield root
            # print("",end='')
        children = root.children
    else:
        children = root
    for child in children:
        if isinstance(child, (Node, list, tuple)):
            if type(child).__name__ in curTypePriority:
                curType = type(child).__name__
            else:
                curType = pre_type
            for node in walk_tree_3(child, curType, curTypePriority):
                if hasattr(node, 'position'):
                    yield node

def walk_tree_all_nodes(root, pre_type):
    children = None
    if isinstance(root, Node):
        curType = type(root).__name__
        if hasattr(root,'position'):
            # if hasattr(root,'curType') and root.curType is not None:
            #     print("")
            root.curType = curType
            yield root
            # print("",end='')
        children = root.children
    else:
        children = root
    for child in children:
        if isinstance(child, (Node, list, tuple)):
            curType = type(child).__name__
            for node in walk_tree_all_nodes(child, curType):
                if hasattr(node, 'position'):
                    yield node

def get_token_stream(root):
    tokens = set()
    for x in walk_tree_2(root, None):
        x = (x.value, (x.position[0],x.position[1]),x.stmt_type,type(x).__name__)
        tokens.add(x)
    return sorted(tokens,key=lambda x:x[1])

def get_token_stream_2(root, typePriority=None, separator=False):
    positions = set()
    for x in walk_tree_3(root, None, typePriority):
        positions.add(x)
    positions = list(positions)
    positions = sorted([((x.position[0],x.position[1]), x.curType) for x in positions if x.position and x.curType])
    if positions.__len__() == 0:
        return positions
    start_line, end_line = positions[0][0][0], positions[-1][0][0]
    mapping = {}
    for x in positions:
        mapping[x[0][0]] = x[1]
    tokens = []
    for token in root.tokens.list:
        if token.position[0] < start_line:
            continue
        elif token.position[0] > end_line:
            break
        elif (type(token).__name__ != "Separator" and separator is False) or separator is True:
            if token.position[0] not in mapping:
                if token.value == 'finally' and type(token).__name__ == 'Keyword':
                    token.curType = 'TryStatement'
                elif token.value in {'if', 'else'} and type(token).__name__ == 'Keyword':
                    token.curType = 'IfStatement'
                else:
                    token.curType = '<UNK>'
            else:
                token.curType = mapping[token.position[0]]
            tokens.append(token)
    return tokens


def dump(ast, file):
    pickle.dump(ast, file)

def load(file):
    return pickle.load(file)
