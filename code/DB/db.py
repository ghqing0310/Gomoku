from collections import defaultdict
import copy
from itertools import combinations
import random
import pisqpipe as pp

class GomokuNode:
    '''state is the board (2-D list), me is 1 and opponent is 2, empty is 0.'''

    ## threat categories:
    ## 0: five and pre-five
    ## 1: pre-straight-four, pre-four
    ## 2: others

    pattern_names = {
    5: {
    (1,1,1,1,1): 'five',
    (1,1,1,1,0): 'pre-five', (1,1,1,0,1): 'pre-five', (1,1,0,1,1): 'pre-five',
    # full permutation = 5, but considering symmetry, 3 is enough.
    (1,1,1,0,0): 'pre-four', (1,1,0,1,0): 'pre-four', (1,0,1,1,0): 'pre-four',
    (0,1,1,1,0): 'pre-four', (1,1,0,0,1): 'pre-four', (1,0,1,0,1): 'pre-four'
    # full permutation = 10, but considering symmetry, 6 is enough.
    },
    6: {
    (0,1,1,1,0,0): 'pre-straight-four', (0,1,1,0,1,0): 'pre-straight-four',
    # full permutation = 4, but considering symmetry, 2 is enough.
    (0,1,1,0,0,0): 'pre-broken-three-3', (0,1,0,0,1,0): 'pre-broken-three-3',
    (0,0,1,0,1,0): 'pre-broken-three-3', (0,0,1,1,0,0): 'pre-broken-three-3'
    },
    7: {
    (0,0,1,1,0,0,0): 'pre-three-2', (0,0,1,0,1,0,0): 'pre-three-2'
    # full permutation = 3, but considering symmetry, 2 is enough.
    }}

    pattern_relys = {
    5: {
    # five
    (1,1,1,1,1): [(1,1,1,1,1)],
    # pre-five
    (1,1,1,1,0): [(1,1,1,1,1)], (1,1,1,0,1): [(1,1,1,1,1)], (1,1,0,1,1): [(1,1,1,1,1)],
    # pre-four
    (1,1,1,0,0): [(1,1,1,1,2),(1,1,1,2,1)], (1,1,0,1,0): [(1,1,1,1,2),(1,1,2,1,1)],
    (1,0,1,1,0): [(1,1,1,1,2),(1,2,1,1,1)], (0,1,1,1,0): [(1,1,1,1,2),(2,1,1,1,1)],
    (1,1,0,0,1): [(1,1,1,2,1),(1,1,2,1,1)], (1,0,1,0,1): [(1,1,1,2,1),(1,2,1,1,1)]
    },
    6: {
    # pre-straight-four
    (0,1,1,1,0,0): [(0,1,1,1,1,0)], (0,1,1,0,1,0): [(0,1,1,1,1,0)],
    # pre-broken-three-3: pre-broken-three + three with 3 rely moves
    (0,1,1,0,0,0): [(2,1,1,2,1,2), (2,1,1,1,2,2)],
    (0,1,0,0,1,0): [(2,1,1,2,1,2), (2,1,2,1,1,2)],
    (0,0,1,0,1,0): [(2,1,1,2,1,2), (2,2,1,1,1,2)],
    (0,0,1,1,0,0): [(2,1,1,1,2,2), (2,2,1,1,1,2)]
    },
    7: {
    # pre-three-2: three with 2 rely moves
    (0,0,1,1,0,0,0): [(0,2,1,1,1,2,0)], (0,0,1,0,1,0,0): [(0,2,1,1,1,2,0)]
    }}

    def __init__(self, type, level, parent, depth, state, operator):
        self.type = type # 'root', 'combination', 'dependency'
        self.level = level
        self.children = []
        self.parent = parent
        self.depth = depth
        self.state = state
        self.size = len(state)
        self.threats = defaultdict(set)
        ## threat:{(0,1,1),(0,2,1),(0,3,1),(0,4,0),(0,5,0)}(frozenset)
        ## rely: ({(0,1,1),(0,2,1),(0,3,1),(0,4,0),(0,5,0)}, {(0,4,0),(0,5,0)},
        ##        {(0,4,1),(0,5,2)})
        ## threats: {'pre-four':{threat+rely1, threat+rely2}, ...}
        self.operator = operator # a tuple of three sets:
                                 # precondition set, add set and delete set
        self.category = 3 # no threat at all
        self.search()

    def isGoalState(self):
        if self.threats.get('five') is not None:
            self.category = 0
            return True
        return False

    def operate(self, operator):
        ''' return a state '''
        newstate = copy.deepcopy(self.state)
        for (i, j, value) in operator[2]:
            newstate[i][j] = value
        return newstate

    def getOperators(self, maxcat):
        ''' returns a generator of tuples of three sets:
        precondition set, add set and delete set.
        operators(precondition set, delete set and add set) are set of tuples,
        where the first and second represent coordinates, and the third is the occupying
        stone.
        i.e. {(0,0,0), (0,1,1), (0,2,1), ...},{(0,0,0)},{(0,0,1)}
        Also, set the node's threat category.'''
        # threat categories 0 first
        if (maxcat > 0) and (self.threats.get('pre-five') is not None):
            self.category = 0
            return list(self.threats.get('pre-five'))
        # threat categories 1 second
        if (maxcat > 1) and (self.threats.get('pre-straight-four') is not None):
            self.category = 1
            return list(self.threats.get('pre-straight-four'))
        if (maxcat > 1) and (self.threats.get('pre-four') is not None):
            self.category = 1
            return list(self.threats.get('pre-four'))
        # threat categories 2
        if (maxcat > 2):
            operators = set()
            for key, value in self.threats.items():
                operators = operators.union(value)
            self.category = 2
            return list(operators)

    def search(self):
        self.searchPattern(5)
        self.searchPattern(6)
        self.searchPattern(7)

    def searchPattern(self, n):
        '''search for patterns of specific number horizontally, vertically and diagonally.
        returns a dictionary of threat patterns.'''
        # horizontal search
        for i in range(self.size):
            for j in range(self.size-n+1):
                self._addSlice((i,)*n, range(j, j+n),
                               tuple(self.state[i][k] for k in range(j, j+n)))
                self._addSlice((i,)*n, range(j+n-1, j-1, -1),
                               tuple(self.state[i][k] for k in range(j+n-1, j-1, -1)))

        # vertical search
        for j in range(self.size):
            for i in range(self.size-n+1):
                self._addSlice(range(i, i+n), (j,)*n,
                               tuple(self.state[k][j] for k in range(i, i+n)))
                self._addSlice(range(i+n-1, i-1, -1), (j,)*n,
                               tuple(self.state[k][j] for k in range(i+n-1, i-1, -1)))

        # diagonal search
        for i in range(n-1, self.size):
            s = i
            for j in range(i-n+2):
                self._addSlice(range(s, s-n, -1), range(j, j+n),
                               tuple(self.state[s-k][j+k] for k in range(n)))
                self._addSlice(range(s-n+1, s+1), range(j+n-1, j-1, -1),
                               tuple(self.state[s-k][j+k] for k in range(n-1, -1, -1)))
                s -= 1
        for j in range(1, self.size-n+1):
            e = j
            for i in range(self.size-1, j+n-2, -1):
                self._addSlice(range(i, i-n, -1), range(e, e+n),
                               tuple(self.state[i-k][e+k] for k in range(n)))
                self._addSlice(range(i-n+1, i+1), range(e+n-1, e-1, -1),
                               tuple(self.state[i-k][e+k] for k in range(n-1, -1, -1)))
                e += 1
        for i in range(self.size-n, -1, -1):
            s = i
            for j in range(self.size-n-i+1):
                 self._addSlice(range(s, s+n), range(j, j+n),
                                tuple(self.state[s+k][j+k] for k in range(n)))
                 self._addSlice(range(s+n-1, s-1, -1), range(j+n-1, j-1, -1),
                                tuple(self.state[s+k][j+k] for k in range(n-1, -1, -1)))
                 s += 1
        for j in range(1, self.size-n+1):
            e = j
            for i in range(self.size-n-j+1):
                 self._addSlice(range(i, i+n), range(e, e+n),
                                tuple(self.state[i+k][e+k] for k in range(n)))
                 self._addSlice(range(i+n-1, i-1, -1), range(e+n-1, e-1, -1),
                                tuple(self.state[i+k][e+k] for k in range(n-1, -1, -1)))
                 e += 1

    def _addSlice(self, rowindex, columnindex, slice, p = False):
        '''helper method to verify if a slice is a threat.
        If yes, add it into the threats dictionary.'''
        if p == True:
            print(rowindex)
            print(columnindex)
            print(slice)
        slice_name = self.pattern_names[len(slice)].get(slice)
        if slice_name is not None:
            threat = frozenset(zip(rowindex, columnindex, slice))
            relies = self.pattern_relys[len(slice)].get(slice)
            for rely in relies:
                deleteset = []
                addset = []
                for i in range(len(slice)):
                    if slice[i] != rely[i]:
                        deleteset.append((rowindex[i], columnindex[i], slice[i]))
                        addset.append((rowindex[i], columnindex[i], rely[i]))
                self.threats[slice_name].add((threat, frozenset(deleteset),
                frozenset(addset)))

class DBProblem:
    def __init__(self, board, check):
        self.root = GomokuNode('root', 0, None, 0, board, None)
        self.treeSizeIncreased = True
        self.goal = None
        self.depth = float('inf')
        self.level = 1
        self.refuted = 0
        self.check = check # check global defend or not

    def addDependencyStage(self, node):
        if node is not None:
            if (self.level == node.level + 1) and (node.type in ['root', 'combination']):
                self.addDependentChildren(node, 1)
            for child in node.children:
                self.addDependencyStage(child)

    def addDependentChildren(self, node, level):
        if (self.goal is None) and (node is not None) and (self.legalOperators(
        node) is not None):  # stop as soon as goal is found
            # first, search for global defensive strategy
            if self.check and node.parent is not None:
                tempNode = GomokuNode('root', 0, None, 0, inverseBoard(node.state), None)
                tempNode.getOperators(node.parent.category)
                if tempNode.category < node.parent.category:
                    self.refuted += 1
                    return
            for operator in self.legalOperators(node):
                if self.applicable(operator, node):
                    newchild = self.linkNewChildToGraph(node, operator)
                    self.treeSizeIncreased = True
                    self.addDependentChildren(newchild, level+1)

    def addCombinationStage(self, node):
        if node is not None:
            if (node.type == 'dependency') and (node.level == self.level):
                self.findAllCombinationNodes(node, self.root)
            for child in node.children:
                self.addCombinationStage(child)

    def findAllCombinationNodes(self, partner, node):
        if node is not None:
            if self.notInConflict(partner, node): # can be combinated
                if node.type == 'dependency':
                    self.addCombinationNode(partner, node)
                for child in node.children:
                    self.findAllCombinationNodes(partner, child)

    def legalOperators(self, node):
        ''' returns a list of tuples of three sets:
        precondition set, add set and delete set.'''
        return node.getOperators(self.maxcat)

    def applicable(self, operator, node):
        '''the selected operator and the node must be eligible for application of meta-operator,
        i.e. the precondition set must intersects with last-added set'''
        if node.operator is None:
            return True
        return len(operator[0].intersection(node.operator[2])) != 0

    def linkNewChildToGraph(self, node, operator):
        if node.type == 'dependency':
            level = node.level
        else:
            level = node.level + 1
        newchild = GomokuNode(type='dependency', level=level, parent=node,
        depth=node.depth+1, state=node.operate(operator), operator=operator)
        node.children.append(newchild)
        if newchild.isGoalState() and newchild.depth < self.depth:
            self.goal = newchild
            self.depth = newchild.depth
            return None
        return newchild

    def notInConflict(self, partner, node):
        '''partner can be changed with combination of node'''
        if node.operator is None:
            return True
        return partner.threats.get(node.operator[0]) is not None

    def addCombinationNode(self, partner, node):
        '''This function works only when the combination of two nodes allows
        at least one application of the meta operator.'''
        if node.operator is None:
            return
        newstate = partner.operate(node.operator)
        newchild = GomokuNode(type='combination', level=partner.level, parent=partner,
        depth=partner.depth+1, state=newstate, operator=node.operator)
        for newoperator in self.legalOperators(newchild):
            if len(newoperator[0].intersection(newchild.operator[2])) != 0:
                # exists at least one operator that can operate on the add set
                partner.children.append(newchild)
                return

    def search(self, maxcat=3):
        '''do the db search'''
        self.maxcat = maxcat
        while (self.level <= 5) and (self.treeSizeIncreased) and (
        self.refuted <= 10
        ): # maximum 5 levels
            self.treeSizeIncreased = False
            self.addDependencyStage(self.root)
            if self.goal is not None:
                break
            self.addCombinationStage(self.root)
            self.level += 1

    def getStep(self, maxcat=3):
        '''while searching, search for categories < maxcat.
        returns a tuple, (threat category, (x,y))
        threat category = 0, 1, 2, 3'''
        self.search(maxcat)
        if self.goal is None:
            # not winnable, category = 3
            return (3, (None, None))
        else:
            node = self.goal
            while node.parent is not None:
                child = node
                node = node.parent
            for (x, y, player) in child.operator[2]:
                if player == 1:
                    return (node.category, (x, y))

def inverseBoard(board):
    '''inverse the board, exchanging black and white'''
    newboard = []
    for i in range(len(board)):
        newboard.append([])
        for j in range(len(board)):
            if board[i][j] == 1:
                newboard[i].append(2)
            elif board[i][j] == 2:
                newboard[i].append(1)
            else:
                newboard[i].append(0)
    return newboard

def findMostPromising(board):
    '''this method is called when the current board has no winning threat.'''
    size = len(board)
    best = (0,0,0) # stores the most promising children (score, i, j)
    for i in range(size):
        for j in range(size):
            if board[i][j] == 0:
                score = getScore(board, i, j)
                if score > best[0]:
                    best = (score, i, j)
    if best[0] != 0:
        return best[1], best[2]
    else:
        return 10,10

scoredict = {(0,0,1,1,1,0,0): 4, (0,1,1,1,0,0): 3,
             (0,1,1,0,1,0): 2, (0,0,1,1,0,0): 2,
             (0,0,1,0,1,0,0): 1}
''' pre-three-2       ooxxxoo        +4
    pre-three-3       oxxxoo         +3
    broken-three      oxxoxo         +2
    open-two          ooxxoo         +2
    broken-two        ooxoxoo        +1 '''

def getScore(board, x, y):
    '''returns the score of a move according to the threat it may bring.'''
    board[x][y] = 1
    score = 0
    size = len(board)
    # horizontal line
    i = x
    for n in [6, 7]:
        for j in range(size-n+1):
            slice = tuple(board[i][k] for k in range(j, j+n))
            score += scoredict.get(slice, 0)
            slice = tuple(board[i][k] for k in range(j+n-1, j-1, -1))
            score += scoredict.get(slice, 0)

    # vertical line
    j = y
    for n in [6, 7]:
        for i in range(size-n+1):
            slice = tuple(board[k][j] for k in range(i, i+n))
            score += scoredict.get(slice, 0)
            slice = tuple(board[k][j] for k in range(i+n-1, i-1, -1))
            score += scoredict.get(slice, 0)

    # diagonal line
    s = abs(y - x)
    for n in [6, 7]:
        if x < y:
            for i in range(size-s-n+1):
                slice = tuple(board[i+k][s+i+k] for k in range(n))
                score += scoredict.get(slice, 0)
                slice = tuple(board[i+k][s+i+k] for k in range(n-1, -1, -1))
                score += scoredict.get(slice, 0)
        else:
            for i in range(size-s-n+1):
                slice = tuple(board[s+i+k][i+k] for k in range(n))
                score += scoredict.get(slice, 0)
                slice = tuple(board[s+i+k][i+k] for k in range(n-1, -1, -1))
                score += scoredict.get(slice, 0)

    s = y + x
    for n in [6, 7]:
        if x + y < size:
            for i in range(s-n+2):
                slice = tuple(board[i+k][s-i-k] for k in range(n))
                score += scoredict.get(slice, 0)
                slice = tuple(board[i+k][s-i-k] for k in range(n-1, -1, -1))
                score += scoredict.get(slice, 0)
        else:
            for i in range(s+1, size-n+1):
                slice = tuple(board[i+k][s-i-k] for k in range(n))
                score += scoredict.get(slice, 0)
                slice = tuple(board[i+k][s-i-k] for k in range(n-1, -1, -1))
                score += scoredict.get(slice, 0)
    board[x][y] = 0
    return score

###testing###
if __name__ == '__main__':
    import test
    board = [[0 for i in range(20)] for i in range(20)]
    # ## TEST CASE 1
    # for (i, j) in [(6,8), (6,9), (7,7), (8,9), (9,6)]:
    #     board[i][j] = 1
    # for (i, j) in [(6,6), (7,6), (8,6), (8,8), (7,10)]:
    #     board[i][j] = 2
    ## TEST CASE 2
    for (i, j) in [(5,0), (15,0), (10,8), (10,10), (9,9), (11,9)]:
        board[i][j] = 1
    for (i, j) in [(6,0), (7,0), (8,0), (12,0), (13,0), (14,0)]:
        board[i][j] = 2
    # ## TEST CASES BY TEACHER
    # list1 = [(8,0),(9,1),(10,0),(9,2)]
    # list2 = [(17,15),(17,16),(15,14),(16,14),(14,16),(14,15),(16,17),(15,17),(13,16)]
    # list3 = [(1,10),(4,10),(5,12),(6,11),(6,10),(7,12),(8,13),(5,11),(4,11),(3,9),
    #          (2,8),(8,11),(7,11),(6,13),(9,10),(5,9),(2,9)]
    # k = 1
    # for (i, j) in list3:
    #     if k % 2 == 1:
    #         board[i][j] = 1
    #     else:
    #         board[i][j] = 2
    #     k += 1
    problem = DBProblem(board, check=True)
    test.printBoard(board)
    print(problem.getStep())
    print(findMostPromising(board))
