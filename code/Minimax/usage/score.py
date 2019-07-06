"""
评分规则：
    连五，100000
    活四, 10000
    活三,死四 1000
    活二,死三 100
    活一,死二 10
"""

SCORE = {"ONE": 10, "TWO": 100, "THREE": 1000, "FOUR": 100000, "FIVE": 10000000,
         "BLOCKED_ONE": 1, "BLOCKED_TWO": 10, "BLOCKED_THREE": 100, "BLOCKED_FOUR": 10000}
