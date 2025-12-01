import pygame
from network import Network
import sys

pygame.font.init()

width = 700
height = 700
win = pygame.display.set_mode((width, height))
pygame.display.set_caption('Client')


def get_player_data():
    if len(sys.argv) > 2:
        try:
            player_id = int(sys.argv[1])
            game_id = int(sys.argv[2])
            if player_id in (0, 1):
                return player_id, game_id
        except ValueError:
            pass
        print('Invalid or missing player ID argument. Defaulting to player 0.')
    return None, None


class Button:
    def __init__(self, text, x, y, color):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.width = 150
        self.height = 100

    def draw(self, win):
        pygame.draw.rect(win, self.color, (self.x, self.y, self.width, self.height))
        font = pygame.font.SysFont('comicsans', 40)
        text = font.render(self.text, 1, (255, 255, 255))
        win.blit(
            text,
            (
                self.x + round(self.width / 2) - round(text.get_width() / 2),
                self.y + round(self.height / 2) - round(text.get_height() / 2),
            ),
        )

    def click(self, pos):
        x1 = pos[0]
        y1 = pos[1]
        if self.x <= x1 <= self.x + self.width and self.y <= y1 <= self.y + self.height:
            return True
        else:
            return False


def redrawWindow(win, game, p):
    win.fill((128, 128, 128))

    font = pygame.font.SysFont('comicsans', 24)
    big = pygame.font.SysFont('comicsans', 50)
    tiny = pygame.font.SysFont('comicsans', 30)

    if game is None:
        text = big.render('No game data', 1, (255, 0, 0))
        win.blit(text, (width // 2 - text.get_width() // 2, height // 2))
        pygame.display.update()
        return

    # 顶部显示比分
    score_text = font.render(
        f'Score - You: {game.wins[p]}  Opp: {game.wins[1 - p]}   Ties: {game.ties}', 1, (0, 0, 0)
    )
    rounds_text = font.render(f'Rounds played: {game.rounds_played}', 1, (0, 0, 0))
    win.blit(score_text, (20, 10))
    win.blit(rounds_text, (20, 35))

    if not game.connected():
        waiting = big.render('Waiting for Player...', 1, (255, 0, 0))
        win.blit(waiting, (width // 2 - waiting.get_width() // 2, height // 2 - 50))
    else:
        # 标题固定位置：Your Move 在左，Opponent 在右
        title = big.render('Your Move', 1, (0, 255, 255))
        opp_title = big.render('Opponent', 1, (0, 255, 255))
        win.blit(title, (80, 90))
        win.blit(opp_title, (380, 90))

        my_move = game.get_player_move(p) or 'Waiting...'
        opp_idx = 1 - p
        opp_went = game.p2Went if opp_idx == 1 else game.p1Went

        # 阶段一：显示双方出招
        if game.bothWent():
            move1 = game.moves[p]
            move2 = game.moves[1 - p]

            # 渲染双方的出招文字
            text_my = big.render(move1, 1, (0, 0, 0))  # 黑色显示自己的招
            text_opp = big.render(move2, 1, (0, 0, 0))  # 黑色显示对方的招

            # [修正] 无论玩家 p 是 0 还是 1，我的出招（text_my）固定放在左边 (100)，
            # 对方出招（text_opp）固定放在右边 (400)。
            win.blit(text_my, (100, 300))
            win.blit(text_opp, (400, 300))

        # 阶段二：显示 Waiting 或 Locked In
        else:
            text_my = big.render(my_move, 1, (0, 0, 0))
            if opp_went:
                text_opp = tiny.render('Locked In', 1, (200, 0, 0))
            else:
                text_opp = big.render('Waiting...', 1, (0, 0, 0))

            # [修正] 无论玩家 p 是 0 还是 1，我的状态（text_my）固定放在左边 (100)，
            # 对方状态（text_opp）固定放在右边 (400)。
            win.blit(text_my, (100, 300))
            win.blit(text_opp, (400, 300))

        # 比赛结束 — 显示重赛/退出选项
        if hasattr(game, 'match_over') and game.match_over:
            mw = game.match_winner()
            if mw is not None:
                if mw == p:
                    end_txt = big.render('Match Over - YOU WIN!', 1, (0, 200, 0))
                else:
                    end_txt = big.render('Match Over - YOU LOSE', 1, (200, 0, 0))
                win.blit(end_txt, (width // 2 - end_txt.get_width() // 2, height // 2 - 150))

            # 显示投票/结果状态
            if hasattr(game, 'rematch_refused') and game.rematch_refused:
                hint = font.render('Opponent declined - Game Over (returning to menu)', 1, (255, 0, 0))
                win.blit(hint, (width // 2 - hint.get_width() // 2, height // 2 - 50))
            elif game.rematch_decided():
                hint = font.render('Waiting for rematch decision...', 1, (0, 0, 0))
                win.blit(hint, (width // 2 - hint.get_width() // 2, height // 2 - 50))
            else:
                hint_yes = font.render('[Y] Rematch  [N] Exit', 1, (0, 0, 0))
                win.blit(hint_yes, (width // 2 - hint_yes.get_width() // 2, height // 2 - 50))

    for btn in btns:
        btn.draw(win)

    pygame.display.update()


btns = [
    Button('Rock', 50, 500, (0, 0, 0)),
    Button('Scissors', 250, 500, (255, 0, 0)),
    Button('Paper', 450, 500, (0, 255, 0)),
]


def main():
    run = True
    clock = pygame.time.Clock()
    n = Network()
    player_data = n.getP()
    player_id, game_id = get_player_data()
    if player_id is None or game_id is None:
        return
    if player_data is None:
        print('ERROR: Failed to get player number from server')
        return

    try:
        player = int(player_data)
    except (ValueError, TypeError) as e:
        print(f'ERROR: Could not convert player to int: {e}')
        return

    print('You are player', player)

    game = None
    last_get_time = 0
    i_went = False
    last_bothWent = False

    while run:
        clock.tick(60)

        current_time = pygame.time.get_ticks()
        # 1. 网络请求（每 100ms 一次）
        if current_time - last_get_time >= 100:
            try:
                game = n.send('get')
            except Exception as e:
                print(f"[client] Send error on 'get': {e}")
                game = None
            last_get_time = current_time

        if game is None:
            pygame.time.delay(50)
            continue

        if player == 0:
            i_went = game.p1Went
        else:
            i_went = game.p2Went

        # 检查是否从 match_over 恢复到正常游戏（reset 后 match_over 变为 False）
        if not game.match_over and last_bothWent:
            print(f'[client] match reset detected, resetting local state')
            last_bothWent = False  # <-- 重置本地标记

        # 2. 核心逻辑：显示回合结果
        if game.bothWent() and not last_bothWent:
            print(f'[client] bothWent detected, showing result')

            # 阶段一：显示双方出招 (Paper vs Scissors)
            # 此时 redrawWindow 已经修改为固定显示：我的招式在左，对手招式在右
            redrawWindow(win, game, player)
            pygame.display.update()
            pygame.time.delay(1000)  # 暂停 1 秒

            # 阶段二：覆盖显示胜负结果 (You Won!)
            font = pygame.font.SysFont('comicsans', 90)
            winner = game.winner()
            if (winner == 1 and player == 1) or (winner == 0 and player == 0):
                text = font.render('You Won!', 1, (255, 0, 0))
            elif winner == -1:
                text = font.render('Tie Game!', 1, (255, 0, 0))
            else:
                text = font.render('You Lost...', 1, (255, 0, 0))

            win.blit(text, (width / 2 - text.get_width() / 2, height / 2 - text.get_height() / 2))
            pygame.display.update()

            # 暂停 2 秒展示胜负结果，期间不发送任何网络包
            pygame.time.delay(2000)

            print(f'[client] waiting for server to reset...')

        last_bothWent = game.bothWent()

        # 3. 事件处理（出招/退出/重赛）
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                pygame.quit()

            if event.type == pygame.KEYDOWN:
                # 处理重赛投票（按 Y/N）
                if hasattr(game, 'match_over') and game.match_over and not game.rematch_decided():
                    if event.key == pygame.K_y:
                        print(f'[client] player {player} voting YES for rematch')
                        try:
                            n.send('rematch_yes')
                        except Exception as e:
                            print(f'[client] Send error rematch_yes: {e}')
                    elif event.key == pygame.K_n:
                        print(f'[client] player {player} voting NO for rematch')
                        try:
                            n.send('rematch_no')
                            # <-- 一方 N 就立刻返回菜单，不用等待
                            run = False
                        except Exception as e:
                            print(f'[client] Send error rematch_no: {e}')

                # 如果对方拒绝，立刻返回菜单
                if hasattr(game, 'rematch_refused') and game.rematch_refused:
                    print(f'[client] rematch refused by opponent, returning to menu')
                    run = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                for btn in btns:
                    if btn.click(pos):
                        move = btn.text.upper()
                        if game is None:
                            break
                        # 只在游戏进行中且还未 match_over 时允许出招
                        if not (hasattr(game, 'match_over') and game.match_over):
                            if player == 0:
                                if not game.p1Went:
                                    print(f'[client] player 0 sending move: {move}')
                                    try:
                                        n.send(move)
                                        i_went = True
                                    except Exception as e:
                                        print(f'[client] Send error move: {e}')
                            else:
                                if not game.p2Went:
                                    print(f'[client] player 1 sending move: {move}')
                                    try:
                                        n.send(move)
                                        i_went = True
                                    except Exception as e:
                                        print(f'[client] Send error move: {e}')
                        break

        # 4. 每次循环末尾刷新画面
        # 除非在 bothWent 的 delay 阶段，否则会持续调用
        redrawWindow(win, game, player)


def menu_screen():
    run = True
    clock = pygame.time.Clock()

    while run:
        clock.tick(60)
        win.fill((128, 128, 128))
        font = pygame.font.SysFont('comicsans', 60)
        text = font.render('Click to Play!', 1, (255, 0, 0))
        win.blit(text, (100, 200))
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                run = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                run = False

    main()


# while True:
#   menu_screen()
if __name__ == '__main__':
    player_id, game_id = get_player_data()

    if player_id is not None:
        main()
    else:
        menu_screen()
