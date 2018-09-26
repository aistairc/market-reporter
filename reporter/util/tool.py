from typing import Generator, Iterable, TypeVar


A = TypeVar('A')


def takeuntil(target: A, xs: Iterable[A]) -> Generator[A, None, A]:
    '''
    >>> list(takeuntil('</s>', ['I', 'am', 'Kirito', '</s>', '</s>', '</s>']))
    ['I', 'am', 'Kirito', '</s>']
    '''
    for x in xs:
        yield x
        if x == target:
            return
