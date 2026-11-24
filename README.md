*This project has been created as part of the 42 curriculum by atajima.*

# Fly-in

## Description

Fly-in routes a fleet of drones from a start zone to an end zone through a
network of connected zones, using **as few simulation turns as possible**.

The program reads a map file (zones, connections, capacities, zone types),
computes a schedule for every drone, and prints the turn-by-turn movements in
the format required by the subject. Every schedule respects:

- zone capacity (`max_drones`) and connection capacity (`max_link_capacity`),
- zone types: `normal` (1 turn), `priority` (1 turn, preferred), `restricted`
  (2 turns, no waiting on the connection), `blocked` (never entered),
- simultaneous moves, where a space freed during a turn can be reused in the
  same turn.

The planner is **exact**: it finds the minimum number of turns for any map, not
an approximation. On all ten maps shipped with the subject it reaches the
reference optimum, including the optional Challenger map (43 turns).

An optional pygame window (`--gui`) shows the simulation.

## Instructions

### Requirements

- Python 3.10 or later
- `make`
- A display, only if you want to use the GUI

### Installation

```sh
make install
```

This creates a virtual environment in `.venv` and installs the dependencies
listed in `requirements.txt`: `pygame-ce` (for the GUI), `flake8` and `mypy`.

#### Why `pygame-ce` instead of `pygame`

This project was developed with Python 3.14. The latest release of the
original `pygame` package (2.6.1) has no prebuilt wheel for Python 3.14, so
`pip install pygame` finds no ready-made package and tries to build it from
source. That build needs a C compiler and the SDL development libraries, and
fails on a normal setup. As a result, `pygame` cannot be installed, and
`import pygame` fails.

`pygame-ce` (Community Edition) is a fork of pygame maintained by former
pygame contributors. It is not a reduced version: it keeps the same API, is
imported with the same name (`import pygame`), and publishes wheels for new
Python versions quickly, including 3.14. No code change is needed to use it.

Do not install both packages in the same environment: they provide the same
`pygame` module and would overwrite each other.

### Running

Pick a map from the `maps/` directory by level and number:

```sh
make maps                          # list every map and the command to run it
make run                           # default: LEVEL=easy NUM=1
make run LEVEL=hard NUM=2          # maps/hard/02_capacity_hell.txt
make gui LEVEL=medium NUM=3        # terminal output + pygame window
make run LEVEL=challenger NUM=1    # The Impossible Dream
```

`LEVEL` is a sub-directory of `maps/` (`easy`, `medium`, `hard`,
`challenger`), and `NUM` selects the file whose name starts with that number
(`2` → `02_*.txt`). Any other file can be run with `MAP`:

```sh
make run MAP=path/to/my_map.txt
```

Or directly:

```sh
.venv/bin/python fly_in.py <map_file> [--gui]
```

Without `--gui`, the program does not need pygame at all.

Exit codes: `0` on success, `1` for an invalid or unsolvable map (with an
error message on stderr), `2` for an unexpected internal error.

### Other Makefile rules

| Rule | Description |
|---|---|
| `make debug` | Run the program under `pdb` (`LEVEL`/`NUM`/`MAP` work here too) |
| `make lint` | `flake8 .` and `mypy .` with the flags required by the subject |
| `make lint-strict` | `flake8 .` and `mypy . --strict` |
| `make clean` | Remove `__pycache__` and `.mypy_cache` |
| `make fclean` | `clean`, then remove the virtual environment |

## Algorithm and implementation strategy

### Pipeline

```
map file ─ MapParser ─> FlyInMap ─ Graph ─> adjacency list
        ─ Planner ─> one timeline per drone ─ Simulation ─> output lines
                                            └ Visualizer ─> pygame window
```

| File | Role |
|---|---|
| `parse.py` | `MapParser`: syntax and validation, one clear error per line |
| `models.py` | Data classes: `Zone`, `Connection`, `FlyInMap`, `ZoneType` |
| `graph.py` | `Graph`: adjacency list, and Dijkstra for a lower bound on turns |
| `flow.py` | `FlowNetwork`: generic max flow and min-cost flow |
| `planner.py` | `TimeExpandedNetwork` and `Planner`: the scheduling itself |
| `simulation.py` | `Simulation`: turns the timelines into output lines |
| `visualizer.py` | `Visualizer`: pygame window showing the simulation |
| `error.py` | Exception hierarchy (`FlyInError` and subclasses) |

### Key idea: a time-expanded flow network

Drones are interchangeable, so the question "can all N drones arrive within T
turns?" becomes "can N units of flow go from source to sink?" in a graph whose
nodes are **(zone, turn)** pairs:

- Each zone at each turn is split into an *in* node and an *out* node joined by
  an edge of capacity `max_drones`. This limits how many drones are in the zone
  at the end of that turn.
- A **wait** is an edge from `(z, t-1)` to `(z, t)`.
- A **move** to a normal or priority zone is an edge from `(u, t-1)` to
  `(v, t)` with capacity `max_link_capacity`.
- A **move to a restricted zone** goes through a *transit* node at turn `t` and
  arrives at `(v, t+1)`. The transit node has no wait edge, so a drone can
  never stay on the connection.
- The end zone sends everything to the sink. A delivered drone is no longer
  tracked. Blocked zones get no nodes at all.

Because capacity is counted at the end of a turn, a drone leaving a zone frees
its place for another drone entering during the same turn. This matches the
subject's single-file column rule.

### Step 1: lower bound and reachability

Dijkstra on the zone graph, with restricted zones costing 2, gives the fewest
turns `d` a single drone needs. If the end cannot be reached, the program
reports `no path from '<start>' to '<end>'` and stops. No search runs forever.

> **Dijkstra's algorithm** finds the shortest distance from one node to every
> other node when all edge costs are non-negative. It keeps a priority queue
> (`heapq`) of nodes ordered by their current best distance. It always takes
> the closest node not yet finalized: no later path can make it shorter, so its
> distance is final. Then it tries to improve the distances of its neighbors.
> Complexity: O((V + E) log V).

#### Why the neighbor check compares distances

In `Graph.shortest_turns`, a neighbor is pushed only when
`next_turns < best_turns.get(edge.to, next_turns + 1)`.

- **What is finalized.** When a zone is popped, its distance from start is
  final. Whether the zone lies on the route to the end is not decided, and is
  not needed: the function returns only a number.
- **What makes the first value the shortest.** In this project the cost of a
  move depends only on the destination zone (1, or 2 for restricted). So the
  first distance recorded for a zone is already the shortest. This follows
  from the heap order and the non-negative costs, not from the comparison.
- **What the check is for.** It stops zones from being pushed again. Without
  it, every move back toward start is pushed too. The heap grows without
  limit, and on an unreachable map the loop never ends:

  | Map | pushes with the check | pushes without |
  |---|---|---|
  | `easy/02_simple_fork` | 4 | 9 |
  | `hard/03_ultimate_challenge` | 30 | 108,934 |
  | `challenger/01_the_impossible_dream` | 53 | stopped at 200,000 |
  | unreachable end | 4 (returns `None`) | never ends |

- **Why `<` and not `if edge.to not in best_turns`.** Here both give the
  same answers and the same number of pushes on every map. The `<` form is
  the standard Dijkstra and stays correct if costs ever depend on the
  connection. The `not in` form is correct only because of the
  destination-only cost rule, and would return wrong turn counts if that rule
  changed.

### Step 2: minimum number of turns (max flow)

Layers are added one turn at a time. From layer `d` on, Edmonds–Karp pushes
more flow, **keeping the flow already found**, until N units reach the sink.
The first T where this happens is the optimum. As a safety net, `d + N - 1`
turns always suffice (send one drone per turn along a shortest path).

> **Edmonds–Karp** computes a maximum flow: how much can go from a source to a
> sink when every edge has a capacity. It repeats two steps until no path is
> left:
>
> 1. Find a path from source to sink in the *residual graph* with BFS, so the
>    path has the fewest edges. The residual graph contains every edge that
>    still has free capacity, and a reverse edge for every edge that already
>    carries flow.
> 2. Push as much flow as the smallest free capacity on that path allows.
>
> Reverse edges let a later path cancel flow sent earlier, which is how the
> algorithm fixes bad early choices. Here one unit of flow is one drone, so
> the maximum flow is the number of drones that can arrive within T turns.
> In `flow.py`, `_bfs()` finds the path and `_push()` sends the flow.

### Step 3: choosing good paths (min-cost flow)

Max flow gives the right T but may pick odd paths. The network for T turns is
rebuilt with costs and solved with min-cost flow (successive shortest paths,
Dijkstra with node potentials):

| Action | Cost | Why |
|---|---|---|
| Wait in the start zone | 0 | Waiting to depart is free |
| Wait elsewhere | 1 | Avoid needless waiting mid-route |
| Move to a priority zone | 2 | Prefer priority zones at equal turn count |
| Move to a normal zone | 3 | |
| Move to a restricted zone | 6 | Two turns of movement |

Waiting is cheaper than any move. So two drones swapping places through the
same connection always cost more than both waiting, and swaps never appear.
This keeps connection capacity shared between both directions.

The flow is then split into one path per drone (its *timeline*), and drones
are numbered D1, D2, … in order of departure.

### Results

| Map | Drones | Turns | Subject optimum |
|---|---|---|---|
| easy 1 / 2 / 3 | 2 / 4 / 4 | 4 / 4 / 4 | 4 / 4 / 4 |
| medium 1 / 2 / 3 | 5 / 6 / 5 | 8 / 10 / 6 | 8 / 10 / 6 |
| hard 1 / 2 / 3 | 8 / 12 / 15 | 13 / 16 / 26 | 13 / 16 / 26 |
| challenger | 25 | 43 | 43 |

### Complexity and memory

V = zones, E = connections, N = drones, T = turns.

- Network size: O(T · (V + E)) nodes and edges, which is also the memory use.
- Step 2: at most N augmenting paths plus one failed BFS per layer, so
  O((N + T) · T · (V + E)).
- Step 3: N Dijkstra runs, O(N · T(V + E) · log(T(V + E))).
- Paths are not recomputed from scratch. Step 2 reuses the flow of previous
  layers, and step 3 runs once.

Measured wall-clock time of `fly_in.py` (Python 3.14, macOS, including
interpreter start-up):

| Map | Drones | Turns | Time |
|---|---|---|---|
| easy maps | 2–4 | 4 | about 0.05 s |
| Challenger | 25 | 43 | about 0.24 s |
| `easy/02_simple_fork` with `nb_drones` changed | 1000 | 502 | about 4.9 s |
| `easy/01_linear_path` with `nb_drones` changed | 1000 | 1002 | about 8.0 s |
| `hard/03_ultimate_challenge` with `nb_drones` changed | 100 | 111 | about 1.1 s |
| `hard/03_ultimate_challenge` with `nb_drones` changed | 500 | 511 | about 28.5 s |
| `hard/03_ultimate_challenge` with `nb_drones` changed | 1000 | 1011 | about 124 s |

Since the number of turns T grows roughly linearly with N, the running time
grows roughly quadratically with the number of drones.

### Known limitation

Connection capacity is enforced per direction inside the network. The cost
design prevents simultaneous opposite 1-turn moves on the same connection.
It does not cover two cases: a 2-turn move into a restricted zone at the same
time as a 1-turn move in the opposite direction, and two opposite 2-turn
moves on a connection between two restricted zones. In these cases, the
combined capacity could in theory be exceeded. This does not happen on any
of the provided maps. See `KNOWN_LIMITATION.md` (in Japanese) for details.

## Visual representation

### Terminal output

One line per turn, as required by the subject:

- `D<ID>-<zone>`: the drone moved into `<zone>` this turn.
- `D<ID>-<zone1>-<zone2>`: the drone is in flight on the connection toward a
  restricted zone, and will land on the next turn.
- Drones that do not move, or are already delivered, are omitted.

### GUI (`--gui`)

The window opens after the terminal output has been printed, and plays the
simulation automatically, one turn about every 0.7 seconds.

- **Zones** are circles at their map coordinates, filled with their `color`
  and labeled with their name. Zones without a color, or with an unknown color
  name such as `rainbow`, are gray.
- **Connections** are lines between zones.
- **Drones** are orange markers. Drones at the same place share one marker,
  which shows how many they are. A drone flying toward a restricted zone is
  drawn halfway along the connection. Delivered drones stay on the end zone,
  so its marker shows how many have arrived so far.
- The current turn is shown in the top-left corner.
- Close the window or press `ESC` to quit.

**How it helps:** the text output tells *what* happens, while the window shows
*where*. You can see how the fleet splits across branches, where drones wait,
and how long a restricted transit lasts.

## Example

Input (`maps/medium/03_priority_puzzle.txt`):

```
nb_drones: 5

start_hub: start 0 0 [color=green]
hub: slow_path1 1 -1 [zone=restricted color=red]
hub: slow_path2 2 -1 [color=red]
hub: fast_junction 1 0 [zone=priority color=blue max_drones=2]
hub: fast_path 2 0 [zone=priority color=blue]
hub: merge_point 3 0 [color=yellow max_drones=3]
end_hub: goal 4 0 [color=green]

connection: start-slow_path1
connection: start-fast_junction
connection: slow_path1-slow_path2
connection: slow_path2-merge_point
connection: fast_junction-fast_path
connection: fast_path-merge_point
connection: merge_point-goal [max_link_capacity=2]
```

Output (6 turns, the optimum):

```
D1-start-slow_path1 D2-fast_junction
D1-slow_path1 D2-fast_path D3-start-slow_path1 D4-fast_junction
D1-slow_path2 D2-merge_point D3-slow_path1 D4-fast_path D5-fast_junction
D1-merge_point D2-goal D3-slow_path2 D4-merge_point D5-fast_path
D1-goal D3-merge_point D4-goal D5-merge_point
D3-goal D5-goal
```

D1 and D3 take the slow restricted branch. `D1-start-slow_path1` is the
in-flight turn, and the drone lands on `slow_path1` on the next turn. D2, D4
and D5 use the priority branch. Queueing everyone on the fast branch would
take 8 turns, because its connections let only one drone through per turn.
Using both branches brings this down to 6.

Error examples:

```
$ .venv/bin/python fly_in.py bad_type.txt
Error: line 4: invalid zone type: 'foo'
$ .venv/bin/python fly_in.py disconnected.txt
Error: no path from 's' to 'g'
```

## Resources

- Python documentation: [`heapq`](https://docs.python.org/3/library/heapq.html),
  [`dataclasses`](https://docs.python.org/3/library/dataclasses.html),
  [`argparse`](https://docs.python.org/3/library/argparse.html).
- [pygame-ce documentation](https://pyga.me/docs/).
- [mypy](https://mypy.readthedocs.io/) and
  [flake8](https://flake8.pycqa.org/) documentation.

### Use of AI

An AI assistant (Claude) was used for the following tasks:

- **Choosing the algorithm**: deciding which optimization algorithm to use.
- **Parser design**: how to split the parser into methods, and how to
  validate the metadata blocks.
- **Compliance review**: checking the project against the subject (flake8,
  mypy, Makefile, README, visual representation).

All AI-generated code was read, run on every provided map, and checked with
`flake8` and `mypy --strict`.

---

<details>
<summary>日本語版</summary>

# Fly-in

## 概要

Fly-in は、つながったゾーンのネットワークを通って、複数のドローンを start
ゾーンから end ゾーンまで**できるだけ少ないターン数で**運ぶプログラム。

マップファイル（ゾーン、接続、容量、ゾーンの種類）を読み込み、全ドローンの
スケジュールを計算して、各ターンの移動を subject 指定の形式で出力する。
スケジュールは必ず次のルールを守る。

- ゾーンの容量（`max_drones`）と接続の容量（`max_link_capacity`）
- ゾーンの種類：`normal`（1ターン）、`priority`（1ターン、優先）、
  `restricted`（2ターン、接続の上で待てない）、`blocked`（入れない）
- 移動は全ドローン同時。ターン中に空いた場所は、同じターンのうちに
  別のドローンが使える

経路計画は**厳密解**で、近似ではなく常に最小ターン数を求める。subject 付属の
10マップすべてで最適値に到達する（任意の Challenger マップの43ターンを含む）。

オプションで pygame のウィンドウ（`--gui`）にシミュレーションを表示できる。

## 使い方

### 必要なもの

- Python 3.10 以上
- `make`
- 画面（GUI を使う場合のみ）

### インストール

```sh
make install
```

`.venv` に仮想環境を作り、`requirements.txt` の依存関係を入れる：
`pygame-ce`（GUI 用）、`flake8`、`mypy`。

#### 本家の `pygame` ではなく `pygame-ce` を使う理由

このプロジェクトは Python 3.14 で開発した。本家 `pygame` の最新版（2.6.1）には
Python 3.14 用のビルド済みパッケージ（wheel）がないため、`pip install pygame`
はソースからのビルドを試みる。このビルドには C コンパイラと SDL の開発用
ライブラリが必要で、普通の環境では失敗する。その結果 `pygame` をインストール
できず、`import pygame` もできない。

`pygame-ce`（Community Edition）は、元 pygame の開発者たちがメンテナンスして
いる pygame のフォーク。簡易版ではなく、API は同じで、import する名前も同じ
（`import pygame`）。新しい Python 向けの wheel も早く公開されており、3.14 にも
対応している。コードを変えずにそのまま使える。

両方を同じ環境に入れてはいけない。どちらも同じ `pygame` モジュールを提供する
ので、互いに上書きしてしまう。

### 実行

`maps/` ディレクトリのマップを、レベルと番号で選んで実行する。

```sh
make maps                          # 全マップと、実行するコマンドの一覧
make run                           # 既定: LEVEL=easy NUM=1
make run LEVEL=hard NUM=2          # maps/hard/02_capacity_hell.txt
make gui LEVEL=medium NUM=3        # ターミナル出力 + pygame ウィンドウ
make run LEVEL=challenger NUM=1    # The Impossible Dream
```

`LEVEL` は `maps/` の下のディレクトリ名（`easy`、`medium`、`hard`、
`challenger`）で、`NUM` はファイル名の先頭の番号（`2` → `02_*.txt`）。
それ以外のファイルは `MAP` で指定する。

```sh
make run MAP=path/to/my_map.txt
```

直接実行する場合：

```sh
.venv/bin/python fly_in.py <map_file> [--gui]
```

`--gui` を付けなければ pygame は不要。

終了コード：成功は `0`、マップが不正・解けない場合は `1`（stderr にエラー
メッセージ）、想定外の内部エラーは `2`。

### その他の Makefile ルール

| ルール | 内容 |
|---|---|
| `make debug` | `pdb` 上で実行する（`LEVEL`/`NUM`/`MAP` も使える） |
| `make lint` | subject 指定のフラグで `flake8 .` と `mypy .` |
| `make lint-strict` | `flake8 .` と `mypy . --strict` |
| `make clean` | `__pycache__` と `.mypy_cache` を削除 |
| `make fclean` | `clean` のあと仮想環境も削除 |

## アルゴリズムと実装方針

### 全体の流れ

```
マップファイル ─ MapParser ─> FlyInMap ─ Graph ─> 隣接リスト
            ─ Planner ─> ドローンごとのタイムライン ─ Simulation ─> 出力行
                                                └ Visualizer ─> pygame ウィンドウ
```

| ファイル | 役割 |
|---|---|
| `parse.py` | `MapParser`：構文チェックと検証。行ごとに分かりやすいエラーを出す |
| `models.py` | データクラス：`Zone`、`Connection`、`FlyInMap`、`ZoneType` |
| `graph.py` | `Graph`：隣接リストと、ターン数の下限を求めるダイクストラ法 |
| `flow.py` | `FlowNetwork`：汎用の最大流・最小費用流 |
| `planner.py` | `TimeExpandedNetwork` と `Planner`：スケジュールの計算 |
| `simulation.py` | `Simulation`：タイムラインを出力行に変換する |
| `visualizer.py` | `Visualizer`：pygame のウィンドウでシミュレーションを表示 |
| `error.py` | 例外の階層（`FlyInError` とそのサブクラス） |

### 中心となる考え方：時間展開フローネットワーク

ドローンは区別しなくていいため、「N 機全部が T ターン以内に着けるか」は、
**（ゾーン, ターン）** の組を頂点にしたグラフで「source から sink に N 単位の
フローを流せるか」という問題になる。

- 各ターンの各ゾーンを *in* と *out* の2頂点に分け、容量 `max_drones` の
  辺でつなぐ。これでターン終了時にそのゾーンにいられる機数が制限される。
- **待機**は `(z, t-1)` から `(z, t)` への辺。
- normal・priority ゾーンへの**移動**は、`(u, t-1)` から `(v, t)` への
  容量 `max_link_capacity` の辺。
- **restricted ゾーンへの移動**は、ターン `t` の*中継*頂点を経由して
  `(v, t+1)` に着く。中継頂点には待機の辺がないので、接続の上に留まれない。
- end ゾーンからは全部 sink に流れる。配達済みのドローンはそれ以上追わない。
  blocked ゾーンは頂点自体を作らない。

容量はターン終了時点で数えるので、ゾーンから出ていったドローンの場所を、
同じターンに入ってくる別のドローンが使える。subject の「一列に並んだ
ドローンが毎ターン1マス進める」ルールを満たす。

### ステップ1：下限と到達可能性

restricted を 2 としてゾーンのグラフにダイクストラ法をかけ、1機だけなら
何ターンで着けるか（`d`）を求める。end に到達できなければ
`no path from '<start>' to '<end>'` と報告して終了する。探索が終わらない
ことはない。

> **ダイクストラ法**は、辺のコストがすべて0以上のグラフで、1つのノードから
> 各ノードへの最短距離を求める。ノードを「今わかっている最短距離」の順に並べた
> 優先度付きキュー（`heapq`）を使う。まだ確定していないノードのうち、一番近い
> ものを取り出す。これより短い経路はあとから見つからないので、その距離は確定
> する。そのあと、隣のノードの距離を更新できるか調べる。
> 計算量は O((V + E) log V)。

#### 隣のゾーンを比較してから候補に入れる理由

`Graph.shortest_turns` では、`next_turns < best_turns.get(edge.to, next_turns + 1)`
のときだけ、隣のゾーンを heap に入れる。

- **何が確定するか**：ゾーンを取り出した時点で確定するのは、start からそのゾーン
  までの最短ターン数。そのゾーンが end への経路に入るかどうかは決まらないし、
  決める必要もない（この関数が返すのはターン数だけ）。
- **最初の値が最短になる理由**：このプロジェクトでは、移動のコストが行き先ゾーンの
  種類だけで決まる（1、restricted は 2）。そのため、あるゾーンに最初に記録された
  値がそのまま最短になる。これを保証しているのは heap が小さい順に取り出すことと、
  コストがマイナスにならないことで、比較ではない。
- **比較（判定）の役割**：記録済みのゾーンを heap に入れ直さないこと。判定がないと
  start へ戻る移動なども毎回入れることになり、heap が際限なく増える。end に
  到達できないマップでは、ループが終わらない。

  | マップ | 判定あり の push 回数 | 判定なし |
  |---|---|---|
  | `easy/02_simple_fork` | 4 | 9 |
  | `hard/03_ultimate_challenge` | 30 | 108,934 |
  | `challenger/01_the_impossible_dream` | 53 | 200,000 回で打ち切り |
  | end に到達できない | 4（`None` を返す） | 終わらない |

- **`if edge.to not in best_turns` ではなく `<` にした理由**：このプロジェクトでは
  どちらも、全マップで答えも push 回数も同じになる。`<` は一般的なダイクストラ法の
  形で、コストが接続ごとに決まるルールに変わっても正しく動く。`not in` が正しいのは
  「コストが行き先だけで決まる」というルールがあるからで、ルールが変わると間違った
  ターン数を返してしまう。

### ステップ2：最小ターン数（最大流）

1ターンずつ層を足していく。`d` 層目からは、Edmonds–Karp 法で、**それまでに
見つけたフローを残したまま**追加分を流し、N 単位が sink に届くまで続ける。
初めて届いた T が最適値。`d + N - 1` ターンあれば必ず全機届く
（最短経路に1ターン1機ずつ送り出せばよい）ので、これを安全のための上限にする。

> **Edmonds–Karp 法**は最大流を求める。最大流とは、各辺に容量があるときに、
> source から sink へ最大でどれだけ流せるかのこと。次の2つを、流せる経路が
> なくなるまで繰り返す。
>
> 1. *残余グラフ*の上で、BFS で source から sink への経路（辺の数が最少のもの）
>    を探す。残余グラフとは、容量に空きがある辺と、すでにフローが流れている
>    辺の逆向きの辺からなるグラフ。
> 2. その経路上で一番小さい空き容量の分だけ流す。
>
> 逆向きの辺を通ると、前に流したフローを取り消せる。これで、最初に選んだ
> 経路がまずくてもあとから直せる。ここではフロー1単位がドローン1機なので、
> 最大流は「T ターン以内に到着できる機数」になる。`flow.py` では `_bfs()` が
> 経路を探し、`_push()` が流す。

### ステップ3：経路の選択（最小費用流）

最大流で T は正しく求まるが、選ぶ経路が不自然なことがある。そこで T ターン分の
ネットワークをコスト付きで作り直し、最小費用流（逐次最短路法、ポテンシャル付き
ダイクストラ法）で解く。

| 動作 | コスト | 理由 |
|---|---|---|
| start で待機 | 0 | 出発を待つのはタダ |
| それ以外で待機 | 1 | 途中での無駄な待機を避ける |
| priority へ移動 | 2 | 同じターン数なら priority を選ぶ |
| normal へ移動 | 3 | |
| restricted へ移動 | 6 | 移動2ターン分 |

待機はどの移動よりも安い。そのため、2機が同じ接続を通って入れ替わるより、
2機とも待つほうが必ず安くなり、入れ替わりは起きない。これで接続の容量を
両方向で共有するルールを守っている。

最後にフローをドローン1機ずつの経路（*タイムライン*）に分け、出発順に
D1, D2, … と番号を振る。

### 結果

| マップ | ドローン数 | ターン数 | subject の最適値 |
|---|---|---|---|
| easy 1 / 2 / 3 | 2 / 4 / 4 | 4 / 4 / 4 | 4 / 4 / 4 |
| medium 1 / 2 / 3 | 5 / 6 / 5 | 8 / 10 / 6 | 8 / 10 / 6 |
| hard 1 / 2 / 3 | 8 / 12 / 15 | 13 / 16 / 26 | 13 / 16 / 26 |
| challenger | 25 | 43 | 43 |

### 計算量とメモリ

V = ゾーン数、E = 接続数、N = ドローン数、T = ターン数。

- ネットワークの大きさ：頂点と辺が O(T · (V + E))。メモリ使用量も同じ。
- ステップ2：増加パスが最大 N 本と、層ごとに失敗する BFS が1回なので、
  O((N + T) · T · (V + E))。
- ステップ3：ダイクストラ法を N 回、O(N · T(V + E) · log(T(V + E)))。
- 経路を毎回ゼロから計算し直してはいない。ステップ2は前の層までのフローを
  使い回し、ステップ3は1回だけ解く。

実測（`fly_in.py` 全体の実行時間。Python 3.14、macOS、インタプリタ起動を含む）：

| マップ | ドローン数 | ターン数 | 時間 |
|---|---|---|---|
| easy マップ | 2〜4 | 4 | 約0.05秒 |
| Challenger | 25 | 43 | 約0.24秒 |
| `easy/02_simple_fork` の `nb_drones` を変更 | 1000 | 502 | 約4.9秒 |
| `easy/01_linear_path` の `nb_drones` を変更 | 1000 | 1002 | 約8.0秒 |
| `hard/03_ultimate_challenge` の `nb_drones` を変更 | 100 | 111 | 約1.1秒 |
| `hard/03_ultimate_challenge` の `nb_drones` を変更 | 500 | 511 | 約28.5秒 |
| `hard/03_ultimate_challenge` の `nb_drones` を変更 | 1000 | 1011 | 約124秒 |

ターン数 T はドローン数 N にほぼ比例して増えるため、実行時間は N のおよそ
2乗で増える。

### 既知の制限

ネットワーク内では、接続の容量を向きごとに設定している。コスト設計によって、
同じ接続で1ターン移動同士が逆向きに同時に通ることは起きない。ただし次の2つは
例外で、理論上は合計の容量を超える可能性がある：restricted への2ターン移動と
逆向きの1ターン移動が重なる場合、restricted 同士を結ぶ接続で逆向きの
2ターン移動が重なる場合。付属のマップではどれも起きていない。
詳細は `KNOWN_LIMITATION.md` を参照。

## ビジュアル表示

### ターミナル出力

subject の指定どおり、1ターン1行で出力する。

- `D<ID>-<zone>`：そのターンにドローンが `<zone>` に移動した。
- `D<ID>-<zone1>-<zone2>`：restricted ゾーンへ向かって接続の上を飛行中で、
  次のターンに着く。
- 動かなかったドローンと、配達済みのドローンは書かない。

### GUI（`--gui`）

ターミナル出力のあとにウィンドウが開き、約0.7秒に1ターンずつ自動で
シミュレーションを再生する。

- **ゾーン**：マップの座標に丸を描き、`color` で塗って名前を書く。色の指定が
  ない場合や、`rainbow` のような知らない色名はグレーにする。
- **接続**：ゾーンの間の線。
- **ドローン**：オレンジの印。同じ場所にいるドローンは1つの印にまとめ、
  機数を書く。restricted へ飛行中のドローンは接続の中間に描く。配達済みの
  ドローンは end に残すので、end の印はそれまでに着いた機数を表す。
- 左上に現在のターンを表示する。
- ウィンドウを閉じるか `ESC` で終了する。

**何が分かりやすくなるか：** 文字の出力は「何が起きたか」を、ウィンドウは
「どこで起きているか」を見せる。機体がどの分岐に振り分けられるか、どこで
待っているか、restricted の通過に何ターンかかるかが目で見て分かる。

## 実行例

入力（`maps/medium/03_priority_puzzle.txt`）と出力（6ターン、最適値）は
英語版の「Example」と同じ。

D1 と D3 は遅い restricted の分岐を通る。`D1-start-slow_path1` は飛行中の
ターンで、次のターンに `slow_path1` に着く。D2、D4、D5 は priority の分岐を
使う。速い分岐の接続は1ターンに1機しか通れないので、全機を速い分岐に
並ばせると8ターンかかる。両方の分岐を使うことで6ターンに縮まる。

エラーの例：

```
$ .venv/bin/python fly_in.py bad_type.txt
Error: line 4: invalid zone type: 'foo'
$ .venv/bin/python fly_in.py disconnected.txt
Error: no path from 's' to 'g'
```

## 参考資料

参考文献の一覧は英語版の「Resources」と同じ。

### AI の利用
- プロジェクトの設計方針
- 使用するアルゴリズムの選定
- パーサーの設計
- subject 要件の確認
</details>
