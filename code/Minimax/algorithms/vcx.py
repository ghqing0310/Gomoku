import numpy as np
import usage.role as R
from usage import config
from usage.score import SCORE
import time

"============="
"=== V C X ==="
"============="
#
# 算杀
# 算杀的原理和极大极小值搜索是一样的
# 不过算杀只考虑冲四活三这类对方必须防守的棋
# 因此算杀的复杂度虽然是 M^N ，但是底数M特别小，可以算到16步以上的杀棋。
# VCT 连续活三胜
# VCF 连续冲四胜利
#

Cache = {
    'vct': {},
    'vcf': {},
}
findMaxCache = {}
findMinCache = {}

MAX_SCORE = SCORE['FOUR']
MIN_SCORE = SCORE['THREE']

lastMaxPoint = None
lastMinPoint = None
There_is_no_points = True


# 找到所有比目标分数大的位置
# 注意，不止要找自己的，还要找对面的
def find_max(b, player, score):
    r = find_get_cache(b, min_=False)
    if r:
        return r
    result = []

    # 能连五，则直接返回
    ai_fives = np.where(b.AIScore >= SCORE['FIVE'])
    if len(ai_fives[0]):
        ll = len(ai_fives[0])
        AIFives = [
            (ai_fives[0][i], ai_fives[1][i])
            for i in range(ll)
        ]
        find_cache(b, AIFives, min_=False)
        return AIFives

    op_fives = np.where(b.OPScore >= SCORE['FIVE'])
    if len(op_fives[0]):
        ll = len(op_fives[0])
        opFives = [
            (op_fives[0][i], op_fives[1][i])
            for i in range(ll)
        ]
        find_cache(b, opFives, min_=False)
        return opFives

    for i in range(b.size):
        for j in range(b.size):
            if b.board[i][j] != R.EMPTY:
                continue
            p = (i, j)
            s = b.AIScore[p[0]][p[1]] if player == R.AI else b.OPScore[p[0]][p[1]]
            b.score[p] = s
            if s >= score:
                result.append(p)

    result.sort(key=lambda x: b.score[x], reverse=True)
    find_cache(b, result, min_=False)
    return result


# MIN层
# 找到所有比目标分数大的位置
def find_min(b, player, score):
    r = find_get_cache(b, min_=True)
    if r:
        return r

    opFives = np.where(b.OPScore >= SCORE['FIVE'])
    if len(opFives[0]):
        find_cache(b, [(opFives[0][0], opFives[1][0])], min_=True)
        return [(opFives[0][0], opFives[1][0])]

    ai_fives = np.where(b.AIScore >= SCORE['FIVE'])
    if len(ai_fives[0]):
        ll = len(ai_fives[0])
        AIFives = [
            (ai_fives[0][i], ai_fives[1][i])
            for i in range(ll)
        ]
        find_cache(b, AIFives, min_=True)
        return AIFives

    result = []
    fours = []
    blockedfours = []
    for i in range(b.size):
        for j in range(b.size):
            if b.board[i][j] == R.EMPTY:
                p = (i, j)
                s1 = b.OPScore[p]
                s2 = b.AIScore[p]

                if s1 >= SCORE['FOUR']:  # 如果对面有开4
                    b.score[p] = s1
                    fours.insert(0, p)
                    continue
                if s2 >= SCORE['FOUR']:  # 如果我有开四
                    b.score[p] = s2
                    fours.append(p)
                    continue
                if s1 >= SCORE['BLOCKED_FOUR']:  # 如果对面有冲4
                    b.score[p] = s1
                    blockedfours.insert(0, p)
                    continue
                if s2 >= SCORE['BLOCKED_FOUR']:
                    b.score[p] = s2
                    blockedfours.append(p)
                    continue
                if s1 >= score or s2 >= score:
                    p = (i, j)
                    b.score[p] = s1
                    result.append(p)

    # 注意冲四，因为虽然冲四的分比活四低，但是他的防守优先级是和活四一样高的，否则会忽略冲四导致获胜的走法
    if fours:
        find_cache(b, fours + blockedfours, min_=True)
        return fours + blockedfours

    # 注意对结果进行排序
    # 因为 fours 可能不存在，这时候不要忽略了 blockedfours
    result = blockedfours + result  # 这里让我返回可能的点
    result.sort(key=lambda x: b.score[x], reverse=True)
    find_cache(b, result, min_=True)
    return result


def get_max(b, player, deep, totalDeep=0):
    global lastMaxPoint, There_is_no_points
    if deep <= 0 or time.clock() - b.startTime > config.vcxTimeLimit:
        return False
    points = find_max(b, player, MAX_SCORE)
    # 先找有没有4的情况
    if points and b.AIScore[points[0]] >= SCORE['FOUR']:
        return [points[0]]

    if len(points) >= 0 and deep <= 1:
        There_is_no_points = False
    if len(points) == 0:
        return False

    for i in range(len(points)):
        p = points[i]

        b.put(p, player, True)
        # 如果是防守对面的冲四，那么不用记下来
        if not b.OPScore[p] >= SCORE['FIVE']:
            # 记录上一次的最好值
            lastMaxPoint = p

        m = get_min(b, R.reverse(player), deep - 1)
        b.remove(p)
        if m:
            # 这里返回下一层的值
            m.insert(0, p)
            return m

    return False


# 只要有一种方式能防守住，就必杀失败
def get_min(b, player, deep):
    global lastMinPoint, There_is_no_points

    if b.win(player):
        return False

    if deep <= 0 or time.clock() - b.startTime > config.vcxTimeLimit:
        return False
    points = find_min(b, player, MIN_SCORE)
    if len(points) > 0 and deep <= 1:
        There_is_no_points = False
    if points and b.OPScore[points[0]] >= SCORE['FOUR']:
        # 如果对面走了最好的点！赢了！
        return False
    if len(points) == 0:
        return False

    cands = []
    for i in range(len(points)):
        p = points[i]
        b.put(p, player, True)
        lastMinPoint = p
        m = get_max(b, R.reverse(player), deep - 1)  # 这个里面对每一种找到必杀！
        b.remove(p)
        if m:
            m.insert(0, p)
            cands.append(m)
            continue
        else:
            # 只要有一种能防守住，因为是对面选择，这个路径的必杀失败！
            return False
    _i = np.random.randint(len(cands))
    # 赢了！随便返回一个？
    result = cands[_i]
    return result


def deeping(b, player, deep, totalDeep):
    # 迭代加深算法
    global lastMinPoint, lastMaxPoint, There_is_no_points, total_deep
    for i in range(1, deep + 1, 2):

        lastMinPoint = None
        lastMaxPoint = None
        There_is_no_points = True
        result = get_max(b, player, i, deep)
        if result:
            break
        if There_is_no_points:
            break

    return result


def vcx(b, player, onlyFour, deep=None):
    deep = config.vcxDeep if deep is None else deep
    global MAX_SCORE, MIN_SCORE
    if deep <= 0:
        return False
    if onlyFour:
        # 计算通过 冲四 赢的
        MAX_SCORE = SCORE['BLOCKED_FOUR']
        MIN_SCORE = SCORE['FIVE']
        result = deeping(b, player, deep, deep)
        if result:
            return result[0]
        return False
    else:
        # 计算通过 活三 赢的
        MAX_SCORE = SCORE['THREE']
        MIN_SCORE = SCORE['BLOCKED_FOUR']
        result = deeping(b, player, deep, deep)
        if result:
            return result[0]
        return result


# 连续冲四
def vcf(b, player, deep):
    c = get_cache(b, True)
    if c:
        return c
    else:
        result = vcx(b, player, True, deep)
        cache(b, result, True)
        return result


# 连续活三
def vct(b, player, deep):
    c = get_cache(b)
    if c:
        return c
    else:
        result = vcx(b, player, False, deep)
        cache(b, result, False)
        return result


def find_cache(b, result, min_=False):
    if not config.cache:
        return
    if min_:
        findMinCache[b.zobrist.boardHashing[0]] = result
    else:
        findMaxCache[b.zobrist.boardHashing[0]] = result


def find_get_cache(self, min_=False):
    if not config.cache:
        return
    if min_:
        result = findMinCache.get(self.zobrist.boardHashing[0], None)
    else:
        result = findMaxCache.get(self.zobrist.boardHashing[0], None)
    return result


def cache(b, result, vcf=False):
    if not config.cache:
        return
    if vcf:
        Cache['vcf'][b.zobrist.boardHashing[0]] = result
    else:
        Cache['vct'][b.zobrist.boardHashing[0]] = result


def get_cache(b, vcf=False):
    if not config.cache:
        return
    if vcf:
        result = Cache['vcf'].get(b.zobrist.boardHashing[0], None)
    else:
        result = Cache['vct'].get(b.zobrist.boardHashing[0], None)
    return result
