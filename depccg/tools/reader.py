
from typing import Tuple, List
from ..tree import Tree
from ..cat import Category
from ..combinator import unknown_combinator
from ..tokens import Token
from lxml import etree
import logging

logger = logging.getLogger(__name__)


UNKNOWN_OP = unknown_combinator()  # TODO


def read_auto(filename, lang='en'):
    for line in open(filename):
        line = line.strip()
        if len(line) == 0:
            continue
        if line.startswith("ID"):
            name = line
        else:
            tree, tokens = Tree.of_auto(line, lang)
            yield name, tokens, tree


def read_xml(filename, lang='en'):
    def parse(tree):
        def rec(node):
            attrib = node.attrib
            if node.tag == 'rule':
                cat = Category.parse(attrib['cat'])
                children = [rec(child) for child in node.getchildren()]
                if len(children) == 1:
                    return Tree.make_unary(cat, children[0], lang)
                else:
                    assert len(children) == 2
                    left, right = children
                    return Tree.make_binary(
                        cat, True, left, right, UNKNOWN_OP, lang)
            else:
                assert node.tag == 'lf'
                cat = Category.parse(attrib['cat'])
                word = attrib['word']
                position = len(tokens)
                token = Token(word=attrib['word'],
                              pos=attrib['pos'],
                              entity=attrib['entity'],
                              lemma=attrib['lemma'],
                              chunk=attrib['chunk'])
                tokens.append(token)
                return Tree.make_terminal(word, cat, position, lang)
        tokens = []
        tree = rec(tree)
        return tree, tokens

    trees = etree.parse(filename).getroot().xpath('ccg')
    for tree in trees:
        name = '_'.join(f'{k}={v}' for k, v in tree.items())
        yield (name,) + parse(tree[0])


def read_jigg_xml(filename, lang='en'):
    # TODO
    def try_get_surface(token):
        if 'word' in token:
            return token.word
        elif 'surf' in token:
            return token.surf
        else:
            raise RuntimeError(
                'the attribute for the token\'s surface form is unknown')

    def parse(tree, tokens):
        counter = 0
        def rec(node):
            nonlocal counter
            attrib = node.attrib
            if 'terminal' not in attrib:
                cat = Category.parse(attrib['category'])
                children = [rec(spans[child]) for child in attrib['child'].split(' ')]
                if len(children) == 1:
                    return Tree.make_unary(cat, children[0], lang)
                else:
                    assert len(children) == 2
                    left, right = children
                    return Tree.make_binary(
                        cat, True, left, right, UNKNOWN_OP, lang)
            else:
                cat = Category.parse(attrib['category'])
                word = try_get_surface(tokens[attrib['terminal']])
                position = counter
                counter += 1
                return Tree.make_terminal(word, cat, position, lang)

        spans = {span.attrib['id']: span for span in tree.xpath('./span')}
        return rec(spans[tree.attrib['root']])

    trees = etree.parse(filename).getroot()
    sentences = trees[0][0].xpath('sentence')
    for sentence in sentences:
        token_and_ids = []
        for token in sentence.xpath('.//token'):
            token_attribs = dict(token.attrib)
            token_id = token_attribs['id']
            for no_need in ['id', 'start', 'cat']:
                if no_need in token_attribs:
                    del token_attribs[no_need]
            token_and_ids.append((token_id, Token(**token_attribs)))
        tokens = [token for _, token in token_and_ids]
        for ccg in sentence.xpath('./ccg'):
            tree = parse(ccg, dict(token_and_ids))
            yield ccg.attrib['id'], tokens, tree


def parse_ptb(tree_string: str, lang='en') -> Tuple[Tree, List[Token]]:
    assert tree_string.startswith('(ROOT ')
    buf = list(reversed(tree_string[6:-1].split(' ')))
    stack = []
    tokens = []
    position = 0

    def reduce(item: str) -> None:
        nonlocal position
        if item[-1] != ')':
            token = Token(word=item)
            tokens.append(token)
            stack.append(item)
            return

        reduce(item[:-1])
        if isinstance(stack[-1], str):
            word = stack.pop()
            category = stack.pop()
            tree = Tree.make_terminal(word, category, position, lang)
            position += 1
        else:
            assert isinstance(stack[-1], Tree)
            children = []
            while isinstance(stack[-1], Tree):
                tree = stack.pop()
                children.append(tree)
            category = stack.pop()
            if len(children) == 1:
                tree = Tree.make_unary(category, children[0], lang)
            elif len(children) == 2:
                right, left = children
                tree = Tree.make_binary(category, True, left, right, UNKNOWN_OP, lang)
            else:
                assert False
        stack.append(tree)

    def rec() -> None:
        if len(buf) == 0:
            return
        item = buf.pop()
        assert item[0] == '(' or item[-1] == ')'
        if item[0] == '(':
            stack.append(Category.parse(item[1:]))
        elif item[-1] == ')':
            reduce(item)
        rec()

    try:
        rec()
        assert len(stack) == 1 and isinstance(stack[0], Tree)
    except:
        raise RuntimeError('Parse failed on an invalid CCG tree')
    return stack[0], tokens


def read_ptb(filename, lang='en'):
    name0 = None
    for i, line in enumerate(open(filename)):
        line = line.strip()
        if len(line) == 0:
            continue
        if line.startswith("ID"):
            name0 = line
        else:
            tree, tokens = parse_ptb(line, lang)
            name = name0 or f'ID={i}'
            yield name, tokens, tree


def read_trees_guess_extension(filename, lang='en'):
    logger.info(f'reading trees from: {filename}')
    if filename.endswith('.jigg.xml'):
        logger.info(f'read it as jigg XML file')
        yield from read_jigg_xml(filename, lang=lang)
    elif filename.endswith('.xml'):
        logger.info(f'read it as C&C XML file')
        yield from read_xml(filename, lang=lang)
    elif filename.endswith('.ptb'):
        logger.info(f'read it as PTB format file')
        yield from read_ptb(filename, lang=lang)
    else:
        logger.info(f'read it as AUTO file')
        yield from read_auto(filename, lang=lang)

