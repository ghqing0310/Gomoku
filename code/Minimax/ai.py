from usage import role as R
import numpy as np
from algorithms.board import Board
from usage import config
from algorithms.vcx import vcf, vct
from algorithms.minimax import minimax


class AI:

    def __init__(self, board):
        self.b = Board(board)
        self.turnChecked = False  # 用来对应非空开局，确定先后手
        self.start = True
        self.searchDeep = config.searchDeep_white
        self.if_found_vcx = False

    def get_move(self):
        if self.start:
            self.start = False
            if np.sum(self.b.board):
                pass
            else:
                return (self.b.size // 2, self.b.size // 2), 1

        p, if_only = minimax(self.b, self.searchDeep, config.spreadLimit)
        return p, if_only

    def get_move_vcx(self):
        if self.start:
            self.start = False
            if np.sum(self.b.board):
                pass
            else:
                return self.b.size // 2, self.b.size // 2
        p = vcf(self.b, R.AI, config.vcxDeep)
        if p:
            return p
        else:
            return vct(self.b, R.AI, config.vcxDeep)

    def set(self, move, player):
        self.b.put(move, player, True)

    def back(self):
        self.b.back()

    def get_opponent_move(self, board):
        for x in range(self.b.size):  # |
            for y in range(self.b.size):  # \
                if self.b.board[x][y] != board[x][y]:
                    # which means the opponent takes move (x, y)
                    return x, y
        return 0

    def white_or_black(self):
        c = 0
        for x in range(self.b.size):  # |
            for y in range(self.b.size):  # \
                if self.b.board[x][y] != R.EMPTY:
                    c += 1
        return (c + 1) % 2  # True for black
