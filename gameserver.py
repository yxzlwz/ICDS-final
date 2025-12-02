import socket
from _thread import start_new_thread
import pickle
import traceback
import time
import threading
from game import Game

server = '0.0.0.0'
port = 5555


games = {}  # gameId -> Game
conns = {}  # gameId -> [conn1, conn2]
idCount = 0
games_lock = threading.Lock()  # <-- 保护 games 和 conns 的锁
reset_pending = {}  # gameId -> True/False 标记是否需要重置
reset_lock = threading.Lock()


def safe_broadcast(gameId):
    """把当前 game 广播给该 gameId 下所有活跃连接（需在 games_lock 内调用）"""
    rem = []
    for c in conns.get(gameId, []):
        try:
            c.sendall(pickle.dumps(games[gameId]))
        except Exception as e:
            print(f'[server] broadcast send error to a conn in game {gameId}: {e}')
            rem.append(c)
    # 清理已失效的连接
    if rem:
        conns[gameId] = [c for c in conns.get(gameId, []) if c not in rem]


def threaded_client(conn, p, gameId):
    global idCount
    try:
        conn.sendall(str(p).encode())
    except Exception as e:
        print(f'[server] Error sending player id to player {p}: {e}')

    try:
        while True:
            data = conn.recv(4096)
            if not data:
                print(f'[server] empty recv from player {p}, closing')
                break

            try:
                data_str = data.decode().strip()
            except Exception:
                print(f'[server] received non-text bytes from player {p}: {data[:40]}')
                continue

            if data_str != 'get':
                print(f"[server] player={p} gameId={gameId} recv='{data_str}'")

            with games_lock:
                if gameId not in games:
                    print(f'[server] gameId {gameId} not found')
                    break

                game = games[gameId]

                # <-- 如果比赛已结束，只处理重赛投票和 "get"，不处理其他命令
                if game.match_over:
                    if data_str == 'get':
                        pass  # 仅请求状态
                    elif data_str == 'rematch_yes':
                        game.set_rematch_vote(p, True)
                        print(f'[server] player {p} voted YES for rematch')
                    elif data_str == 'rematch_no':
                        game.set_rematch_vote(p, False)
                        print(f'[server] player {p} voted NO for rematch')
                    else:
                        # 忽略其他命令（包括误发的 "get" 重复或其他数据）
                        if 'get' not in data_str:
                            game.play(p, data_str)
                            print(
                                f'[server] after play: moves={game.moves} p1Went={game.p1Went} p2Went={game.p2Went}'
                            )
                        print(f"[server] ignored command '{data_str}' during match_over")
                # ... (前文代码)
                else:
                    # 比赛进行中，正常处理出招
                    if data_str == 'get':
                        pass
                    # [修改] 增加白名单验证，防止 "getget" 或乱码进入 game.play 导致崩溃
                    elif data_str in ['ROCK', 'PAPER', 'SCISSORS', 'rematch_yes', 'rematch_no']:
                        game.play(p, data_str)
                        print(
                            f'[server] after play: moves={game.moves} p1Went={game.p1Went} p2Went={game.p2Went}'
                        )
                    else:
                        # 忽略其他非法指令
                        pass
                # 广播当前状态给该局的所有连接
                try:
                    safe_broadcast(gameId)
                    if data_str != 'get' and not game.match_over:
                        print(f'[server] broadcasted game {gameId}: moves={game.moves} wins={game.wins}')
                except Exception as e:
                    print(f'[server] broadcast error: {e}')

                bothWent_flag = game.bothWent() and not game.match_over  # <-- 仅在比赛进行中处理 bothWent

                if bothWent_flag:
                    with reset_lock:
                        if gameId not in reset_pending:
                            reset_pending[gameId] = True
                            should_reset = True
                        else:
                            should_reset = False
                else:
                    should_reset = False

                # 检查重赛投票是否已决
                rematch_decided_flag = game.rematch_decided() and game.match_over
                should_handle_rematch = False
                if rematch_decided_flag:
                    should_handle_rematch = True

            # <-- lock 释放

            if should_reset:
                print(f'[server] bothWent for game {gameId}, sleeping 2.0s to let clients show result')
                time.sleep(2.0)

                with games_lock:
                    if gameId in games:
                        game = games[gameId]
                        safe_broadcast(gameId)
                        print(
                            f'[server] re-broadcasted result state: moves={game.moves} winner={game.winner()}'
                        )

                        if game.is_match_over():
                            game.match_over = True
                            game.rematch_votes = [None, None]  # <-- 重置投票
                            safe_broadcast(gameId)
                            print(f'[server] match over for game {gameId}, winner={game.match_winner()}')
                            with reset_lock:
                                if gameId in reset_pending:
                                    del reset_pending[gameId]
                        else:
                            game.resetRound()
                            safe_broadcast(gameId)
                            print(
                                f'[server] reset round for game {gameId} and broadcasted reset state: moves={game.moves}'
                            )
                            with reset_lock:
                                if gameId in reset_pending:
                                    del reset_pending[gameId]

            # 处理重赛投票结果
            if should_handle_rematch:
                with games_lock:
                    if gameId in games:
                        game = games[gameId]
                        # <-- 先检查是否有人拒绝（只要有一个 False 就拒绝）
                        if game.rematch_votes[0] is False or game.rematch_votes[1] is False:
                            # 有一方拒绝，立刻标记并广播
                            game.rematch_refused = True
                            safe_broadcast(gameId)
                            print(f'[server] rematch refused (player voted NO), game {gameId} ending')
                        elif game.rematch_agreed():
                            # 双方都同意重赛
                            print(f'[server] both players agreed to rematch for game {gameId}')
                            game.resetMatch()
                            game.rematch_votes = [None, None]
                            safe_broadcast(gameId)
                            print(f'[server] match reset and broadcasted')

    except Exception as e:
        print(f'[server] Exception in threaded_client for player {p}: {e}')
        traceback.print_exc()
    finally:
        print(f'[server] Lost connection for player {p}')
        with games_lock:
            try:
                if gameId in conns and conn in conns[gameId]:
                    conns[gameId].remove(conn)
            except Exception:
                pass
        try:
            idCount -= 1
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def main():
    global idCount
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((server, port))
    except socket.error as e:
        print(e)

    s.listen(2)
    print('Waiting for a connection, Server Started')
    # 接受连接并维护 conns 列表
    while True:
        conn, addr = s.accept()
        print('Connected to:', addr)
        idCount += 1
        p = 0
        gameId = (idCount - 1) // 2

        with games_lock:
            if idCount % 2 == 1:
                games[gameId] = Game(gameId)
                conns[gameId] = [conn]
                print('Creating a new game...')
            else:
                conns[gameId].append(conn)
                games[gameId].ready = True
                p = 1

        start_new_thread(threaded_client, (conn, p, gameId))


if __name__ == '__main__':
    main()
