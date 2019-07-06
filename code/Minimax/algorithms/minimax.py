from usage import role as R
from usage import config
import time
from usage.score import SCORE


def fix_four(type_score):
    if SCORE['BLOCKED_FOUR'] <= type_score < SCORE['BLOCKED_FOUR'] + SCORE['THREE']:
        return SCORE['THREE'] - 1

    if SCORE['BLOCKED_THREE'] <= type_score < SCORE['THREE']:
        return SCORE['TWO'] - 1

    if type_score == SCORE['TWO']:
        return type_score + 10

    return type_score


def get_value(b, player, position, deep, spread_l, alpha, beta):
    # 这个函数得到的值应该是 player 下了这个点之后的 reward
    # 所以这里还没下
    # 先看看能不能 win
    if b.win(player, position):
        return b.MAX if player == R.AI else b.MIN

    # 然后下这个子
    b.put(position, player, True)

    if time.clock() - b.startTime > config.timeLimit:
        b.remove(position)
        return 0.5

    # 如果是叶结点
    if deep <= 0:
        reward = b.evaluate()
        # 记得撤掉之前 player 下的子
        if b.win(R.reverse(player)):
            b.remove(position)
            if player == R.AI:
                return b.MIN
            elif player == R.OP:
                return b.MAX
        b.remove(position)
        return reward

    result = 0
    star_spread = True if deep <= config.searchDeep_white - 1 else False
    # MIN
    if player == R.AI:
        result = min_value(b, R.OP, deep - 1, spread_l, alpha, beta, star_spread)
    # MAX
    if player == R.OP:
        result = max_value(b, R.AI, deep - 1, spread_l, alpha, beta, star_spread)

    # 撤掉之前 player 下的子
    b.remove(position)
    return result


def max_value(b, player, deep, spread_l, alpha, beta, star_spread):
    v = b.MIN
    candidates = b.gen(player, star_spread = star_spread)
    candidates = candidates[:spread_l]
    for point in candidates:
        v = max(v, get_value(b, player, point, deep, spread_l, alpha, beta))
        if v >= beta:
            return v
        alpha = max(v, alpha)
    return v


def min_value(b, player, deep, spread_l, alpha, beta, star_spread):
    v = b.MAX
    candidates = b.gen(player, star_spread = star_spread)
    candidates = candidates[:spread_l]
    for point in candidates:
        v = min(v, get_value(b, player, point, deep, spread_l, alpha, beta))
        if v <= alpha:
            return v
        beta = min(v, beta)
    return v


def minimax(b, deep, spread_l, star_spread=False):
    b.MIN = -1 * SCORE['FIVE'] * 10
    b.MAX = SCORE['FIVE'] * 10
    best_points = []
    best = b.MIN

    # 生成可选点，最开始的时候不要开启star搜索
    candidates = b.gen(R.AI)
    if len(candidates) == 1:
        return candidates[0], 1
    cand_len = len(candidates)
    for i in range(cand_len):
        point = candidates[i]
        # 超时判断
        if time.clock() - b.startTime > config.timeLimit:
            break
        deep_fixed, spread_l = fix_deep(deep, spread_l, cand_len)
        v = get_value(b, R.AI, point, deep_fixed, spread_l, b.MIN, b.MAX)
        # 如果比之前的一个好，则把当前位置加入待选位置
        if v == best:
            best_points.append(point)
        if v > best:
            best = v
            best_points = [point]
    best_points.sort(key=lambda x: fix_four(b.AIScore[x]), reverse=True)
    result = best_points[0]

    return result, 0


def fix_deep(deep, spread_l, l):
    if l <= 4:
        return deep + 2, spread_l // 2
    if l >= 8:
        return deep - 2, spread_l + 2
    return deep, spread_l

