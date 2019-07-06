from usage import role as R
from usage.score import SCORE
import numpy as np
from usage import config
from usage.zobrist import Zobrist
from usage.pointCache import pointCache

count = 0
total = 0


def fix_score(score):
    if SCORE["FOUR"] > score >= SCORE["BLOCKED_FOUR"]:
        if SCORE["BLOCKED_FOUR"] <= score < (SCORE["BLOCKED_FOUR"] + SCORE["THREE"]):
            # 单独冲四，意义不大
            return SCORE["THREE"]
        elif (SCORE["BLOCKED_FOUR"] + SCORE["THREE"]) <= score < (SCORE["BLOCKED_FOUR"] * 2):
            # 冲四活三
            return SCORE["FOUR"]
        else:
            # 双冲四
            return SCORE["FOUR"] * 2
    return score


class Board:

    def __init__(self, board):
        self.board = np.array(board).copy()
        assert len(board) == len(board[0]), "board is not square"
        self.size = len(board)

        self.AIScoreCache = {}
        self.OPScoreCache = {}
        self.patternCacheCache = {}
        self.genCache = {}
        self.gen3Cache = {}  # onlyThree

        self.steps = []
        self.allSteps = []

        self.zobrist = Zobrist(self.size)
        self.zobrist.init()  # 注意重新初始化
        self._last = [False, False]  # 记录最后一步

        self.startTime = None
        self.neighborCache = {} # self.has_neighbour的缓存

        # 存储双方得分
        self.AIScore = np.zeros([self.size, self.size])
        self.OPScore = np.zeros([self.size, self.size])

        # 玩家X在方向'--', '|', '\', '/'上的得分
        # self.pointCache.get(self.patternCache[X][position[0]][position[1]][Y], 0)[X-1]
        self.patternCache = np.zeros([3, self.size, self.size, 4], dtype='int64')

        self.init_score()

        self.attackRate = config.attackRate

    def init_score(self):
        self.attack = {} # 标记位置属于防守还是进攻
        self.score = {} # 标记位置的最大得分
        self.role = {} # 标记位置的角色
        self.pointCache = pointCache

        # 初始化pattern分数，主要用于应对靠近边上的点
        for i in range(self.size):
            for j in range(self.size):
                if 5 <= i < self.size - 5 and 5 <= j < self.size - 5:
                    continue
                # --
                for k in range(1, 6):
                    y = j - k
                    if y < 0:
                        self.patternCache[R.AI][i][j][0] += R.OP * R.MM ** (5 + k)
                        self.patternCache[R.OP][i][j][0] += R.AI * R.MM ** (5 + k)
                        break
                for k in range(1, 6):
                    y = j + k
                    if y >= self.size:
                        self.patternCache[R.AI][i][j][0] += R.OP * R.MM ** (5 - k)
                        self.patternCache[R.OP][i][j][0] += R.AI * R.MM ** (5 - k)
                        break
                # |
                for k in range(1, 6):
                    x = i - k
                    if x < 0:
                        self.patternCache[R.AI][i][j][1] += R.OP * R.MM ** (5 + k)
                        self.patternCache[R.OP][i][j][1] += R.AI * R.MM ** (5 + k)
                        break
                for k in range(1, 6):
                    x = i + k
                    if x >= self.size:
                        self.patternCache[R.AI][i][j][1] += R.OP * R.MM ** (5 - k)
                        self.patternCache[R.OP][i][j][1] += R.AI * R.MM ** (5 - k)
                        break
                # \
                for k in range(1, 6):
                    x, y = i - k, j - k
                    if x < 0 or y < 0:
                        self.patternCache[R.AI][i][j][2] += R.OP * R.MM ** (5 + k)
                        self.patternCache[R.OP][i][j][2] += R.AI * R.MM ** (5 + k)
                        break
                for k in range(1, 6):
                    x, y = i + k, j + k
                    if x >= self.size or y >= self.size:
                        self.patternCache[R.AI][i][j][2] += R.OP * R.MM ** (5 - k)
                        self.patternCache[R.OP][i][j][2] += R.AI * R.MM ** (5 - k)
                        break
                    # /
                for k in range(1, 6):
                    x, y = i - k, j + k
                    if x < 0 or y >= self.size:
                        self.patternCache[R.AI][i][j][3] += R.OP * R.MM ** (5 + k)
                        self.patternCache[R.OP][i][j][3] += R.AI * R.MM ** (5 + k)
                        break
                for k in range(1, 6):
                    x, y = i + k, j - k
                    if x >= self.size or y < 0:
                        self.patternCache[R.AI][i][j][3] += R.OP * R.MM ** (5 - k)
                        self.patternCache[R.OP][i][j][3] += R.AI * R.MM ** (5 - k)
                        break

        for i in range(self.size):
            for j in range(self.size):
                if self.board[i, j] != R.EMPTY:
                    self.update_score((i, j))
                    self.allSteps.append((i, j))

    def score_cache(self):
        self.AIScoreCache[self.zobrist.boardHashing[0]] = self.AIScore.copy()
        self.OPScoreCache[self.zobrist.boardHashing[0]] = self.OPScore.copy()
        self.patternCacheCache[self.zobrist.boardHashing[0]] = self.patternCache.copy()

    def get_score_cache(self):
        ai_score = self.AIScoreCache.get(self.zobrist.boardHashing[0], None)
        op_score = self.OPScoreCache.get(self.zobrist.boardHashing[0], None)
        pattern_score = self.patternCacheCache.get(self.zobrist.boardHashing[0], None)
        return ai_score, op_score, pattern_score

    def update_score(self, position, remove=False):
        # score cache with Zobrist
        ais, ops, patterns = self.get_score_cache()
        if ais is None:
            pass
        else:
            self.AIScore = ais
            self.OPScore = ops
            self.patternCache = patterns
            return

        # 更新 pattern, 再更新分数
        if_remove = -1 if remove else 1
        radius = 6
        player = self.board[position[0]][position[1]]
        updated_positions = []
        # 无论是不是空位，都需要更新
        # --
        for k in range(0, radius):
            x, y = position[0], position[1] - k
            if y < 0:
                break
            self.patternCache[R.AI][x][y][0] += player * R.MM ** (5 - k) * if_remove
            self.patternCache[R.OP][x][y][0] += player * R.MM ** (5 - k) * if_remove
            updated_positions.append((x, y))
        for k in range(1, radius):
            x, y = position[0], position[1] + k
            if y >= self.size:
                break
            self.patternCache[R.AI][x][y][0] += player * R.MM ** (5 + k) * if_remove
            self.patternCache[R.OP][x][y][0] += player * R.MM ** (5 + k) * if_remove
            updated_positions.append((x, y))
        # |
        for k in range(0, radius):
            x, y = position[0] - k, position[1]
            if x < 0:
                break
            self.patternCache[R.AI][x][y][1] += player * R.MM ** (5 - k) * if_remove
            self.patternCache[R.OP][x][y][1] += player * R.MM ** (5 - k) * if_remove
            updated_positions.append((x, y))
        for k in range(1, radius):
            x, y = position[0] + k, position[1]
            if x >= self.size:
                break
            self.patternCache[R.AI][x][y][1] += player * R.MM ** (5 + k) * if_remove
            self.patternCache[R.OP][x][y][1] += player * R.MM ** (5 + k) * if_remove
            updated_positions.append((x, y))
        # \
        for k in range(0, radius):
            x, y = position[0] - k, position[1] - k
            if x < 0 or y < 0:
                break
            self.patternCache[R.AI][x][y][2] += player * R.MM ** (5 - k) * if_remove
            self.patternCache[R.OP][x][y][2] += player * R.MM ** (5 - k) * if_remove
            updated_positions.append((x, y))
        for k in range(1, radius):
            x, y = position[0] + k, position[1] + k
            if x >= self.size or y >= self.size:
                break
            self.patternCache[R.AI][x][y][2] += player * R.MM ** (5 + k) * if_remove
            self.patternCache[R.OP][x][y][2] += player * R.MM ** (5 + k) * if_remove
            updated_positions.append((x, y))
        # /
        for k in range(0, radius):
            x, y = position[0] - k, position[1] + k
            if x < 0 or y >= self.size:
                break
            self.patternCache[R.AI][x][y][3] += player * R.MM ** (5 - k) * if_remove
            self.patternCache[R.OP][x][y][3] += player * R.MM ** (5 - k) * if_remove
            updated_positions.append((x, y))
        for k in range(1, radius):
            x, y = position[0] + k, position[1] - k
            if x >= self.size or y < 0:
                break
            self.patternCache[R.AI][x][y][3] += player * R.MM ** (5 + k) * if_remove
            self.patternCache[R.OP][x][y][3] += player * R.MM ** (5 + k) * if_remove
            updated_positions.append((x, y))

        # 一次性更新所有需要更新分数的点
        for p in updated_positions:
            self.AIScore[p] = self.score_point(p, R.AI)
            self.OPScore[p] = self.score_point(p, R.OP)

    def score_point(self, position, player):
        result = 0
        pattern = self.patternCache[player][position[0]][position[1]][0]
        result += self.pointCache[pattern][player - 1]
        pattern = self.patternCache[player][position[0]][position[1]][1]
        result += self.pointCache[pattern][player - 1]
        pattern = self.patternCache[player][position[0]][position[1]][2]
        result += self.pointCache[pattern][player - 1]
        pattern = self.patternCache[player][position[0]][position[1]][3]
        result += self.pointCache[pattern][player - 1]
        return result

    # 下子
    def put(self, position, player, record):
        if config.debug:
            print(player, 'put [', position, ']')
        self.board[position] = player
        # 开启分数缓存
        self.score_cache()
        self.zobrist.go(position, player)
        if record:
            self.update_score(position)
            self.allSteps.append(position)

    # 该角色下的最后一步棋
    def last(self, player):
        for i in range(len(self.allSteps) - 1):
            p = self.allSteps[-i]
            if self.board[p] == player:
                return p
        return False

    # 移除棋子
    def remove(self, position):
        r = self.board[position]
        if config.debug:
            print(r, 'remove [', position, ']')
        self.zobrist.go(position, r)
        self.update_score(position, remove=True)
        self.allSteps.pop()
        self.board[position] = R.EMPTY

    # 悔棋
    def back(self):
        if len(self.steps) < 2:
            return
        step = self.steps.pop()
        self.zobrist.go(step, self.board[step])
        self.board[step] = R.EMPTY
        self.update_score(step)
        self.allSteps.pop()
        step = self.steps.pop()
        self.zobrist.go(step, self.board[step])
        self.board[step] = R.EMPTY
        self.update_score(step)
        self.allSteps.pop()

    def evaluate(self):
        self.AIMaxScore = 0
        self.OPMaxScore = 0

        # 遍历出最高分
        for i in range(self.size):
            for j in range(self.size):
                if self.board[i, j] == R.AI:
                    self.AIMaxScore = max(self.AIScore[i, j], self.AIMaxScore)
                elif self.board[i, j] == R.OP:
                    self.OPMaxScore = max(self.OPScore[i, j], self.OPMaxScore)

        self.AIMaxScore = fix_score(self.AIMaxScore)
        self.OPMaxScore = fix_score(self.OPMaxScore)
        result = self.AIMaxScore - self.OPMaxScore * self.attackRate

        return result

    def cache(self, result, only_three=False):
        if not config.cache:
            return
        if only_three:
            self.gen3Cache[self.zobrist.boardHashing[0]] = result
        else:
            self.genCache[self.zobrist.boardHashing[0]] = result

    def get_cache(self, only_three=False):
        if not config.cache:
            return
        if only_three:
            result = self.gen3Cache.get(self.zobrist.boardHashing[0], None)
        else:
            result = self.genCache.get(self.zobrist.boardHashing[0], None)
        return result

    def gen(self, player, only_three=False, star_spread=False):
        r = self.get_cache(only_three)
        if r:
            return r

        fives = []
        ai_fours = []
        op_fours = []
        ai_blocked_fours = []
        op_blocked_fours = []
        ai_two_threes = []
        op_two_threes = []
        ai_threes = []
        op_threes = []
        ai_twos = []
        op_twos = []
        neighbors = []

        potential_neighbors = self.neighborCache.get(self.zobrist.boardHashing[0], None)
        if potential_neighbors is None:
            if len(self.allSteps) <= 2:
                potential_neighbors = self.get_neighbors(distance=2, count=1)
            else:
                potential_neighbors = self.get_neighbors(distance=2, count=2)

        # if star_spread:
        #     for p in potential_neighbors:
        #         score_op = self.OPScore[p]
        #         score_ai = self.AIScore[p]
        #         max_score = max(score_op, score_ai)
        #         self.score[p] = max_score
        #         self.role[p] = player
        #         if max_score >= SCORE['THREE']:
        #             self.attack[p] = 1

        def star_to(p, points):
            if p is None or len(points) == 0:
                return False
            for pp in points:
                if abs(p[0]-pp[0]) > 4 or abs(p[1] - pp[1]) > 4:
                    return False
                if p[0] != pp[0] and p[1] != pp[1] and abs(p[0]-pp[0]) != abs(p[1]-pp[1]):
                    return False
            return True

        for p in potential_neighbors:
            score_op = self.OPScore[p]
            score_ai = self.AIScore[p]
            max_score = max(score_op, score_ai)
            self.score[p] = max_score
            self.role[p] = player

            if star_spread:
                if max_score >= SCORE['FOUR']:
                    pass
                elif star_to(p, self.allSteps):
                    pass
                else:
                    continue

            if score_ai >= score_op:
                if score_ai >= SCORE['FIVE']:
                    # 先看电脑能不能连成 5
                    self.cache([p], only_three)
                    return [p]
                elif score_ai >= SCORE['FOUR']:
                    ai_fours.append(p)
                elif score_ai >= SCORE['BLOCKED_FOUR']:
                    ai_blocked_fours.append(p)
                elif score_ai >= 2 * SCORE['THREE']:  # 能成双三也很强
                    ai_two_threes.append(p)
                elif score_ai >= SCORE['THREE']:
                    ai_threes.append(p)
                elif score_ai >= SCORE['TWO']:
                    ai_twos.append(p)
                else:
                    neighbors.append(p)
            else:
                if score_op >= SCORE['FIVE']:
                    # 再看玩家能不能连成 5
                    # 别急着返回，因为遍历还没完成，说不定电脑自己能成五
                    fives.append(p)
                elif score_op >= SCORE['FOUR']:
                    op_fours.append(p)
                elif score_op >= SCORE['BLOCKED_FOUR']:
                    op_blocked_fours.append(p)
                elif score_op >= 2 * SCORE['THREE']:
                    op_two_threes.append(p)
                elif score_op >= SCORE['THREE']:
                    op_threes.append(p)
                elif score_op >= SCORE['TWO']:
                    op_twos.append(p)
                else:
                    neighbors.append(p)

        # 如果成五，是必杀棋，直接返回
        if fives:
            self.cache(fives, only_three)
            return fives
        # 自己能活四，则直接活四，不考虑冲四
        if player == R.AI and ai_fours:
            self.cache(ai_fours, only_three)
            return ai_fours
        if player == R.OP and op_fours:
            self.cache(op_fours, only_three)
            return op_fours

        # 对面有活四冲四，自己冲四都没，则只考虑对面活四 （此时对面冲四就不用考虑了)
        if player == R.AI and op_fours and not ai_blocked_fours:
            self.cache(op_fours, only_three)
            return op_fours
        if player == R.OP and ai_fours and not op_blocked_fours:
            self.cache(ai_fours, only_three)
            return ai_fours

        # 对面有活四自己有冲四，则都考虑下
        fours = ai_fours + op_fours if player == R.AI else op_fours + ai_fours
        blocked_fours = ai_blocked_fours + op_blocked_fours if player == R.OP else op_blocked_fours + ai_blocked_fours
        if fours:
            self.cache(fours + blocked_fours, only_three)
            return fours + blocked_fours

        result = []
        if player == R.AI:
            result = ai_two_threes + op_two_threes \
                     + ai_blocked_fours \
                     + op_blocked_fours \
                     + ai_threes \
                     + op_threes
        if player == R.OP:
            result = op_two_threes + ai_two_threes \
                     + op_blocked_fours \
                     + ai_blocked_fours \
                     + op_threes \
                     + ai_threes

        # 限制长度
        result = result[:config.countLimit]

        # 双三很特殊，因为能形成双三的不一定比一个活三强
        if ai_two_threes or op_two_threes:
            self.cache(result, only_three)
            return result

        # 只返回大于等于活三的棋
        if only_three:
            self.cache(result, only_three)
            return result

        if player == R.AI:
            twos = ai_twos + op_twos
        else:
            twos = op_twos + ai_twos

        # 从大到小排序
        twos.sort(key=lambda x: self.score.get(x, 0), reverse=True)
        _toExtend = twos if twos else neighbors
        result.extend(_toExtend)

        # 这种分数低的，就不用全部计算了
        self.cache(result[:config.countLimit], only_three)
        return result[:config.countLimit]

    def has_neighbor(self, position, distance, count):
        if self.board[position] == R.EMPTY:
            start_x = max(position[0] - distance, 0)
            end_x = min(position[0] + distance + 1, self.size)
            start_y = max(position[1] - distance, 0)
            end_y = min(position[1] + distance + 1, self.size)
            if np.sum(self.board[start_x:end_x, start_y:end_y] != R.EMPTY) >= count:
                return True
            else:
                return False
        else:
            start_x = max(position[0] - distance, 0)
            end_x = min(position[0] + distance + 1, self.size)
            start_y = max(position[1] - distance, 0)
            end_y = min(position[1] + distance + 1, self.size)
            if np.sum(self.board[start_x:end_x, start_y:end_y] != R.EMPTY) >= count + 1:
                return True
            else:
                return False

    def get_neighbors(self, distance, count):
        result = []
        for i in range(self.size):
            for j in range(self.size):
                if self.board[i][j] != R.EMPTY:
                    continue
                if self.has_neighbor((i, j), distance, count):
                    result.append((i, j))
        self.neighborCache[self.zobrist.boardHashing[0]] = result
        return result

    # 判断 player 下了这个点之后有没有成 5
    def win(self, player, position=None):
        if position is None:
            if player == R.AI:
                five = np.max(self.AIScore)
            else:
                five = np.max(self.OPScore)
            if five >= SCORE['FIVE']:
                return player
        else:
            if player == R.AI:
                r = self.AIScore[position[0]][position[1]]
            else:
                r = self.OPScore[position[0]][position[1]]
            if r >= SCORE['FIVE']:
                return player

        return False

