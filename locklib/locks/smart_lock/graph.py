from collections import defaultdict
from threading import Lock
from typing import DefaultDict, List, Optional, Set

from locklib.errors import DeadLockError


class LocksGraph:
    def __init__(self) -> None:
        self.links: DefaultDict[int, Set[int]] = defaultdict(set)
        self.lock: Lock = Lock()

    def add_link(self, _from: int, to: int) -> None:
        cycle_with = self.search_cycles(to, _from)
        if cycle_with is not None:
            if len(cycle_with) > 2:
                cycle_with.reverse()
                listing_cycle_with = ', '.join([str(x) for x in cycle_with])
                message_tail = f' The full path of the cycle: {listing_cycle_with}.'
            else:
                message_tail = ''
            raise DeadLockError(f'A cycle between {_from}th and {to}th threads has been detected.{message_tail}')
        self.links[_from].add(to)

    def delete_link(self, _from: int, to: int) -> None:
        if _from in self.links:
            if to in self.links[_from]:
                self.links[_from].remove(to)
            if not self.links[_from]:
                del self.links[_from]

    def get_links_from(self, _from: int) -> Set[int]:
        return self.links[_from]

    def dfs(self, path: List[int], current_node: int, target: int) -> Optional[List[int]]:
        path.append(current_node)

        neighbors = self.get_links_from(current_node)

        if neighbors:
            for link in neighbors:
                if link == target:
                    path.append(target)
                    return path
                result_of_next_search = self.dfs(path, link, target)
                if result_of_next_search is not None:
                    return result_of_next_search

        path.pop()
        return None

    def search_cycles(self, _from: int, to: int) -> Optional[List[int]]:
        return self.dfs([], _from, to)
