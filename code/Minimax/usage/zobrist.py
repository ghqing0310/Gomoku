import usage.role as rl
import numpy as np

class Zobrist:
    def __init__(self, size):
        self.size = size

    def init(self):
        self.AIHashing = np.random.randint(9223372036854775807, size=(20, 20), dtype='int64')
        self.OPHashing = np.random.randint(9223372036854775807, size=(20, 20), dtype='int64')
        # 随机数
        self.boardHashing = np.random.randint(9223372036854775807, size=1, dtype='int64')

    def go(self, position, player):
        if player == rl.AI:
            self.boardHashing ^= self.AIHashing[position]
        elif player == rl.OP:
            self.boardHashing ^= self.OPHashing[position]
        else:
            assert 0, "empty do not take hashing move"
