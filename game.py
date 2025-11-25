class Game:
    """
    支持每一回合判胜以及整场三局两胜（first-to-2）计数。
    用法：
      - play(player, move) 在收到玩家出招时调用
      - bothWent() 检查本回合是否两人都已出手
      - winner() 返回本回合胜负：0/1 表示玩家胜利，-1 表示平局或未决
      - is_match_over() 检查三局两胜是否结束
      - match_winner() 返回比赛胜者（0 或 1），若未结束则返回 None
      - resetRound() 清理回合状态，resetMatch() 重置整场比分
    """
    def __init__(self, id):
        self.p1Went = False
        self.p2Went = False
        self.ready = False
        self.id = id
        self.moves = [None, None]
        self.wins = [0, 0]   # 比赛总胜场数
        self.ties = 0
        self.rounds_played = 0
        self._last_round_winner = None  # -1/0/1
        self.match_over = False
        # <-- 添加重赛协商状态
        self.rematch_votes = [None, None]  # [player0的选择, player1的选择]，None/True/False
    
    def get_player_move(self, p):
        return self.moves[p]

    def play(self, player, move):
        """记录单回合出招并在两人都出手后统计该回合胜负（不自动清除回合数据）。"""
        self.moves[player] = move
        if player == 0:
            self.p1Went = True
        else:
            self.p2Went = True

        if self.bothWent():
            # 立即计算本回合胜负并更新比赛比分
            r = self._compute_round_winner()
            self._last_round_winner = r
            if r == -1:
                self.ties += 1
            elif r in (0, 1):
                self.wins[r] += 1
            self.rounds_played += 1

    def connected(self):
        return self.ready

    def bothWent(self):
        return self.p1Went and self.p2Went

    def _compute_round_winner(self):
        """内部方法：假设 moves 都已存在，返回 -1/0/1。"""
        if self.moves[0] is None or self.moves[1] is None:
            return -1

        p1 = self.moves[0].upper()
        p2 = self.moves[1].upper()

        if p1 == p2:
            return -1

        if (p1 == "ROCK" and p2 == "SCISSORS") or \
           (p1 == "SCISSORS" and p2 == "PAPER") or \
           (p1 == "PAPER" and p2 == "ROCK"):
            return 0

        return 1

    def winner(self):
        """
        返回本回合胜负：
          -1 表示平局或尚未两人都出手
           0 或 1 表示该回合胜者
        """
        if not self.bothWent():
            return -1
        return self._last_round_winner if self._last_round_winner is not None else self._compute_round_winner()

    def is_match_over(self):
        """三局两胜：任意一方达到 2 胜则比赛结束。"""
        return self.wins[0] >= 2 or self.wins[1] >= 2

    def match_winner(self):
        """若比赛结束返回 0 或 1，未结束返回 None。"""
        if self.wins[0] >= 2:
            return 0
        if self.wins[1] >= 2:
            return 1
        return None

    def resetRound(self):
        """只重置回合相关状态（用于开始下一回合），不清除累计比分。"""
        self.p1Went = False
        self.p2Went = False
        self.moves = [None, None]
        self._last_round_winner = None

    def resetMatch(self):
        """重置整场比赛（比分与回合都清空）。"""
        self.resetRound()
        self.wins = [0, 0]
        self.ties = 0
        self.rounds_played = 0
        self._last_round_winner = None
        self.match_over = False  # <-- 清空 match_over 标志
        self.rematch_votes = [None, None]  # <-- 清空投票
        if hasattr(self, 'rematch_refused'):
            delattr(self, 'rematch_refused')  # <-- 删除拒绝标记

    def set_rematch_vote(self, player, agree):
        """玩家投票是否同意重赛。True=同意，False=拒绝"""
        self.rematch_votes[player] = agree

    def rematch_agreed(self):
        """两方是否都同意重赛"""
        return self.rematch_votes[0] is True and self.rematch_votes[1] is True

    def rematch_decided(self):
        """是否两方都已投票"""
        return self.rematch_votes[0] is not None and self.rematch_votes[1] is not None
