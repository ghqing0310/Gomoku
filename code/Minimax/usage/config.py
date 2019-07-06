# config
opening = True   # 使用开局库
searchDeep_black = 5   # 搜索深度
searchDeep_white = 15  # 搜索深度
countLimit = 15  # gen函数返回的节点数量上限，超过之后将会按照分数进行截断
timeLimit = 9   # MINIMAX 至多算 x 秒
vcxTimeLimit = 11  # VCX至少算 10 - x 秒
vcxDeep = 15      # 算杀深度
attackRate = 1  # 玄学

random = False   # 在分数差不多的时候是不是随机选择一个走
log = False
# 下面几个设置都是用来提升搜索速度的
spreadLimit = 10  # 单步延伸 长度限制
star = False     # 是否开启 starspread
cache = True     # 使用缓存, 其实只有搜索的缓存有用，其他缓存几乎无用。因为只有搜索的缓存命中后就能剪掉一整个分支，
                 # 这个分支一般会包含很多个点。而在其他地方加缓存，每次命中只能剪掉一个点，影响不大。
window = False   # 启用期望窗口，由于用的模糊比较，所以和期望窗口是有冲突的

# 调试
debug = False     # 打印详细的debug信息
debug2 = False     # 打印每一个候选点的得分
debug3 = False    # 打印 MINI-MAX 搜索的具体步骤
debugGen = False  # 调试启发式搜索函数
debugVCX = False   # 算杀debug
debugAB = False    # 重构 alpha-beta MINIMAX 搜索的信息