from __future__ import annotations
import dataclasses
import typing
import collections

KeyType = typing.TypeVar('KeyType')
ElementType = typing.TypeVar('ElementType')

@dataclasses.dataclass
class PQueue(typing.Generic[KeyType, ElementType]):
    keyfunc: typing.Callable[[ElementType],KeyType] = dataclasses.field(default_factory=lambda x: x)
    elements: typing.Dict[KeyType, typing.List[ElementType]] = dataclasses.field(default_factory=dict)
    keys: typing.List[KeyType] = dataclasses.field(default_factory=list)
    ct: int = 0
    
    @classmethod
    def from_iterable(cls, 
        keyfunc: typing.Callable[[ElementType],KeyType], 
        new_elements: typing.Iterable[ElementType],
    ) -> PQueue[KeyType, ElementType]:
        return cls(elements=new_elements, keys=list(new_elements.keys()))
    
    def append(self, element: ElementType) -> None:
        key = self.keyfunc(element)
        if key not in self.elements:
            self.add_new_key(key)
        self.elements[key].append(element)
        self.ct += 1
    
    def add_new_key(self, key: KeyType) -> None:
        self.elements[key] = []
        self.keys.append(key)
        self.sorted_keys = sorted(self.keys)
    
    def dequeue(self) -> ElementType:
        key = self.keys.pop(0)
        self.ct -= 1
        return self.elements[key].pop(0)

