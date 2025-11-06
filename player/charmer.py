from __future__ import annotations
# Pure translation of the provided JS worker (half-edges + negamax with extra-turn sign rule).
# Interface: def make_move(game_state) -> (r, c, 'H'|'V')

import math
import random
from typing import List, Tuple, Dict, Optional

# ----- Constants (as in JS) -----
DEADEND = -1
REMOVED = -2
EATLOONEY = 10000001
GIVELOONEY = 10000002
GIVEINDEP = 10000  # used as: tag = -GIVEINDEP - index

# ----- Negamax (extra-turn sign rule) -----
class _Stats:
    def __init__(self) -> None:
        self.nodes = 0
        self.leaves = 0
stats = _Stats()

def _negamax(st: "DotsAndBoxesState", depth: int, alpha: float, beta: float) -> float:
    stats.nodes += 1
    if depth == 0 or st.gameIsOver():
        stats.leaves += 1
        return st.evaluate()

    children = st.listMoves()
    if not children:
        return st.evaluate()

    best = -math.inf
    for child in children:
        # negate only if the mover flips (captures keep turn)
        multiplier = st.whoToMove * child.whoToMove
        if multiplier == -1:
            val = -_negamax(child, depth - 1, -beta, -alpha)
        else:
            val =  _negamax(child, depth - 1,  alpha,  beta)
        if val > best:
            best = val
        if best >= beta:
            break
        alpha = max(alpha, best)
    return best

def _reset_stats() -> None:
    stats.nodes = 0
    stats.leaves = 0

# ----- Half-edge state -----
class DotsAndBoxesState:
    def __init__(self,
                 otherHe: List[int],
                 nextHe: List[int],
                 heLengths: List[int],
                 indeps: List[int],
                 indepAreChains: List[bool],
                 looneyValue: int,
                 score: int,
                 whoToMove: int) -> None:
        self.otherHe = otherHe
        self.nextHe = nextHe
        self.heLengths = heLengths
        self.indeps = indeps
        self.indepAreChains = indepAreChains
        self.looneyValue = looneyValue
        self.score = score     # net to the player about to move
        self.whoToMove = whoToMove  # +1 or -1

    def clone(self) -> "DotsAndBoxesState":
        return DotsAndBoxesState(
            self.otherHe[:],
            self.nextHe[:],
            self.heLengths[:],
            self.indeps[:],
            self.indepAreChains[:],
            self.looneyValue,
            self.score,
            self.whoToMove
        )

    def numBoxesLeft(self) -> int:
        counted = [None] * len(self.otherHe)
        s = self.looneyValue

        # joints (cycles in nextHe)
        for he in range(len(self.otherHe)):
            if self.otherHe[he] != REMOVED and counted[he] != REMOVED:
                s += 1
                nHe = he
                counted[he] = REMOVED
                while he != self.nextHe[nHe]:
                    nHe = self.nextHe[nHe]
                    counted[nHe] = REMOVED

        counted = [None] * len(self.otherHe)
        # chains (paired across boxes)
        for he in range(len(self.otherHe)):
            if self.otherHe[he] != REMOVED and counted[he] != REMOVED:
                s += self.heLengths[he]
                counted[he] = REMOVED
                oHe = self.otherHe[he]
                if oHe != DEADEND:
                    counted[oHe] = REMOVED

        for v in self.indeps:
            s += v
        return s

    def gameIsOver(self) -> bool:
        return self.numBoxesLeft() == 0

    def evaluate(self) -> float:
        num_left = self.numBoxesLeft() * 100
        points = self.score * 100
        if self.looneyValue != 0:
            half_remaining = num_left % 200
            return float(points + (num_left + half_remaining) / 2)
        return float(points)

    def simplifyLink(self, he: int) -> None:
        he1 = self.nextHe[he]
        if he1 == DEADEND:
            return
        he2 = self.nextHe[he1]
        if he1 != he and he2 == he:
            otherHe1 = self.otherHe[he1]
            otherHe2 = self.otherHe[he2]

            if otherHe1 == he2:
                # loop
                self.indeps.append(1 + self.heLengths[otherHe2])
                self.indepAreChains.append(False)
            else:
                length = 1 + self.heLengths[he1] + self.heLengths[he2]
                if otherHe1 != DEADEND:
                    self.otherHe[otherHe1] = otherHe2
                    self.heLengths[otherHe1] = length
                if otherHe2 != DEADEND:
                    self.otherHe[otherHe2] = otherHe1
                    self.heLengths[otherHe2] = length
                if otherHe1 == DEADEND and otherHe2 == DEADEND:
                    self.indeps.append(length)
                    self.indepAreChains.append(True)

            self.heLengths[he1] = self.heLengths[he2] = REMOVED
            self.otherHe[he1] = self.otherHe[he2] = REMOVED
            self.nextHe[he1] = self.nextHe[he2] = REMOVED

    def removeHe(self, he: int) -> None:
        oHe = self.otherHe[he]
        self.otherHe[he] = REMOVED
        nHe = he
        while self.nextHe[nHe] != he:
            nHe = self.nextHe[nHe]
        self.nextHe[nHe] = self.nextHe[he]
        self.nextHe[he] = REMOVED
        self.heLengths[he] = REMOVED
        # (JS does not directly change otherHe[oHe] here.)

    def listMoves(self, heList: Optional[List[int]] = None) -> List["DotsAndBoxesState"]:
        ret: List[DotsAndBoxesState] = []

        if self.looneyValue > 0:
            # eat and keep turn
            st = self.clone()
            st.score += self.looneyValue
            st.looneyValue = 0
            ret.append(st)
            if heList is not None: heList.append(EATLOONEY)
            # give and pass turn
            st = self.clone()
            st.score *= -1
            st.whoToMove *= -1
            st.score += self.looneyValue
            st.looneyValue = 0
            ret.append(st)
            if heList is not None: heList.append(GIVELOONEY)
            return ret

        for he in range(len(self.otherHe)):
            if self.otherHe[he] == REMOVED:
                continue
            oHe = self.otherHe[he]
            length = self.heLengths[he]
            if he < oHe:
                continue  # handle pair once

            st = self.clone()
            # detect loop by local cycle structure
            isLoop = (
                self.nextHe[he] == oHe
                or self.nextHe[self.nextHe[he]] == oHe
                or self.nextHe[self.nextHe[self.nextHe[he]]] == oHe
            )

            he3 = REMOVED
            if isLoop:
                if (
                    self.nextHe[he] == he
                    or self.nextHe[self.nextHe[he]] == he
                    or self.nextHe[self.nextHe[self.nextHe[he]]] == he
                ):
                    he3 = he
                    while he3 == he or he3 == oHe:
                        he3 = self.nextHe[he3]
                    length += self.heLengths[he3] + 1

            nHe = self.nextHe[he]
            noHe = self.nextHe[oHe] if oHe != DEADEND else REMOVED

            st.removeHe(he)
            if oHe != DEADEND:
                st.removeHe(oHe)

            st.simplifyLink(nHe)
            if noHe != DEADEND:
                st.simplifyLink(noHe)

            if he3 != REMOVED:
                oHe3 = self.otherHe[he3]
                st.removeHe(he3)
                if oHe3 != DEADEND:
                    st.removeHe(oHe3)
                    st.simplifyLink(oHe3)

            leaveNumber = 2
            st.whoToMove *= -1
            st.score *= -1

            if length > leaveNumber:
                st.score += length - leaveNumber
                st.looneyValue = leaveNumber
            else:
                st.score += length
                st.looneyValue = 0

            if heList is not None: heList.append(he)
            ret.append(st)

        # break smallest independent loop and smallest independent chain
        minChain = math.inf; minLoop = math.inf
        iChain = -1; iLoop = -1
        for i, L in enumerate(self.indeps):
            if self.indepAreChains[i]:
                if L < minChain: minChain, iChain = L, i
            else:
                if L < minLoop:  minLoop, iLoop  = L, i

        def _break_indep(index: int) -> None:
            st = self.clone()
            if st.indepAreChains[index]:
                leaveNumber, minNumber = 2, 3
            else:
                leaveNumber, minNumber = 4, 4
            st.whoToMove *= -1
            st.score *= -1
            L = st.indeps[index]
            if L >= minNumber:
                st.looneyValue = leaveNumber
                st.score += L - leaveNumber
            else:
                st.score += L
                st.looneyValue = 0
            st.indeps.pop(index)
            st.indepAreChains.pop(index)
            ret.append(st)
            if heList is not None: heList.append(-GIVEINDEP - index)

        if iLoop > -1:  _break_indep(iLoop)
        if iChain > -1: _break_indep(iChain)
        return ret

# ----- Build half-edges from the current board -----
def _assignHEIndices(vhLines: List[List[bool]],
                     vhToHEA: List[List[int]],
                     vhToHEB: List[List[int]],
                     otherHe: List[int]) -> None:
    for x in range(len(vhLines)):
        vhToHEA[x] = []
        vhToHEB[x] = []
        for y in range(len(vhLines[x])):
            if not vhLines[x][y]:
                if x == 0:
                    vhToHEB[x].append(len(otherHe))
                    otherHe.append(DEADEND)
                    vhToHEA[x].append(REMOVED)
                elif x == len(vhLines) - 1:
                    vhToHEA[x].append(len(otherHe))
                    otherHe.append(DEADEND)
                    vhToHEB[x].append(REMOVED)
                else:
                    a = len(otherHe); b = a + 1
                    vhToHEA[x].append(a)
                    vhToHEB[x].append(b)
                    otherHe.append(b)
                    otherHe.append(a)
            else:
                vhToHEA[x].append(REMOVED)
                vhToHEB[x].append(REMOVED)

def _heToCoords(he: int,
                vLeft: List[List[int]], vRight: List[List[int]],
                hUp: List[List[int]],   hDown: List[List[int]]) -> Tuple[int,int,int,int,str]:
    # verticals
    for x in range(len(vLeft)):
        for y in range(len(vLeft[x])):
            if vLeft[x][y] == he:
                return (x, y, x, y + 1, "left")
            if vRight[x][y] == he:
                return (x, y, x, y + 1, "right")
    # horizontals
    for y in range(len(hUp)):
        for x in range(len(hUp[y])):
            if hUp[y][x] == he:
                return (x, y, x + 1, y, "up")
            if hDown[y][x] == he:
                return (x, y, x + 1, y, "down")
    raise RuntimeError("he not found")

def _coords_to_move(x1: int, y1: int, x2: int, y2: int) -> Tuple[int,int,str]:
    # horizontal if y1==y2 and x2==x1+1
    if y1 == y2 and x2 == x1 + 1:
        return (y1, x1, 'H')
    # vertical if x1==x2 and y2==y1+1
    if x1 == x2 and y2 == y1 + 1:
        return (y1, x1, 'V')
    raise RuntimeError("invalid segment")

def _consider(hLines: List[List[bool]], vLines: List[List[bool]], currentScore: int) -> Tuple[int,int,str]:
    otherHe: List[int] = []
    nextHe:  List[int] = []
    heLen:   List[int] = []

    vLeft:  List[List[int]] = [[] for _ in range(len(vLines))]
    vRight: List[List[int]] = [[] for _ in range(len(vLines))]
    hUp:    List[List[int]] = [[] for _ in range(len(hLines))]
    hDown:  List[List[int]] = [[] for _ in range(len(hLines))]

    _assignHEIndices(vLines, vLeft, vRight, otherHe)
    _assignHEIndices(hLines, hUp,   hDown,  otherHe)

    # init arrays
    nextHe = [DEADEND] * len(otherHe)
    heLen  = [0]       * len(otherHe)

    # build cycles for each box
    for x in range(len(vLines) - 1):
        for y in range(len(hLines) - 1):
            HEs: List[int] = []
            if not vLines[x][y]:     HEs.append(vRight[x][y])   # right edge of (x,y)
            if not vLines[x+1][y]:   HEs.append(vLeft[x+1][y])  # left edge of (x+1,y)
            if not hLines[y][x]:     HEs.append(hDown[y][x])    # bottom edge of (x,y)
            if not hLines[y+1][x]:   HEs.append(hUp[y+1][x])    # top edge of (x,y+1)
            for i, he in enumerate(HEs):
                if he != REMOVED:
                    nxt = HEs[(i + 1) % len(HEs)]
                    nextHe[he] = nxt
                    # heLen[he] left as 0

    gameState = DotsAndBoxesState(
        otherHe=otherHe, nextHe=nextHe, heLengths=heLen,
        indeps=[], indepAreChains=[], looneyValue=0,
        score=0, whoToMove=1
    )
    unsimpl = gameState.clone()

    # simplify all joints, collect indeps
    indepsToHe: List[int] = []
    old = 0
    for he in range(len(gameState.nextHe)):
        gameState.simplifyLink(he)
        if len(gameState.indeps) > old:
            indepsToHe.append(he)
            old += 1

    # free squares and classify
    looneyHe = None
    loops: List[int] = []
    chains: List[int] = []
    for he in range(len(gameState.nextHe)):
        if gameState.nextHe[he] == he:
            oHe = gameState.otherHe[he]
            if gameState.nextHe[oHe] == gameState.otherHe[he]:
                # broken loop
                if heLen[he] != 2:
                    x1,y1,x2,y2,_ = _heToCoords(he, vLeft, vRight, hUp, hDown)
                    return _coords_to_move(x1,y1,x2,y2)
                else:
                    loops.append(he)
                    looneyHe = he
            else:
                # broken chain
                if gameState.heLengths[he] != 1:
                    x1,y1,x2,y2,_ = _heToCoords(he, vLeft, vRight, hUp, hDown)
                    return _coords_to_move(x1,y1,x2,y2)
                else:
                    chains.append(he)
                    looneyHe = he

    if len(chains) > 0 and len(loops) > 0:
        he = loops[0]
        x1,y1,x2,y2,_ = _heToCoords(he, vLeft, vRight, hUp, hDown)
        return _coords_to_move(x1,y1,x2,y2)

    if len(chains) > 1:
        he = chains[0]
        x1,y1,x2,y2,_ = _heToCoords(he, vLeft, vRight, hUp, hDown)
        return _coords_to_move(x1,y1,x2,y2)

    if len(loops) > 2:
        he = loops[0]
        x1,y1,x2,y2,_ = _heToCoords(he, vLeft, vRight, hUp, hDown)
        return _coords_to_move(x1,y1,x2,y2)

    # looney detection
    if len(chains) == 1:
        gameState.looneyValue = 2
    if len(loops) == 2:
        gameState.looneyValue = 4
    if gameState.looneyValue > 0 and looneyHe is not None:
        oHe = gameState.otherHe[looneyHe]
        gameState.removeHe(looneyHe)
        if oHe != DEADEND:
            noHe = gameState.nextHe[oHe]
            gameState.removeHe(oHe)
            gameState.simplifyLink(noHe)

    # canonical search root, use currentScore from caller
    gameState = DotsAndBoxesState(
        otherHe=gameState.otherHe, nextHe=gameState.nextHe, heLengths=gameState.heLengths,
        indeps=gameState.indeps, indepAreChains=gameState.indepAreChains,
        looneyValue=gameState.looneyValue, score=currentScore, whoToMove=1
    )

    heList: List[int] = []
    children = gameState.listMoves(heList)
    scores = [{"child": ch, "he": heList[i], "val": -math.inf} for i, ch in enumerate(children)]

    MAX_DEPTH = 9  # tune as needed
    bestEdgeHe = None
    for depth in range(1, MAX_DEPTH + 1):
        _reset_stats()
        bestVal = -math.inf
        for s in scores:
            child = s["child"]
            mult = child.whoToMove
            if mult == -1:
                val = -_negamax(child, depth - 1, -math.inf, -bestVal)
            else:
                val =  _negamax(child, depth - 1,  bestVal,  math.inf)
            s["val"] = max(s["val"], val)
            if s["val"] > bestVal:
                bestVal = s["val"]
        scores.sort(key=lambda x: x["val"], reverse=True)
        bestEdgeHe = scores[0]["he"]

    # translate chosen half-edge to a board edge
    if gameState.looneyValue > 0 and looneyHe is not None:
        if bestEdgeHe == EATLOONEY:
            x1,y1,x2,y2,_ = _heToCoords(looneyHe, vLeft, vRight, hUp, hDown)
            return _coords_to_move(x1,y1,x2,y2)
        if bestEdgeHe == GIVELOONEY:
            he2 = unsimpl.otherHe[looneyHe]
            nxt = unsimpl.nextHe[he2]
            x1,y1,x2,y2,_ = _heToCoords(nxt, vLeft, vRight, hUp, hDown)
            return _coords_to_move(x1,y1,x2,y2)
    elif bestEdgeHe <= -GIVEINDEP:
        idx = -bestEdgeHe - GIVEINDEP
        indepHe = indepsToHe[idx]
        if gameState.indeps[idx] == 2 and unsimpl.otherHe[indepHe] == DEADEND:
            nxt = unsimpl.nextHe[indepHe]
            x1,y1,x2,y2,_ = _heToCoords(nxt, vLeft, vRight, hUp, hDown)
            return _coords_to_move(x1,y1,x2,y2)
        else:
            x1,y1,x2,y2,_ = _heToCoords(indepHe, vLeft, vRight, hUp, hDown)
            return _coords_to_move(x1,y1,x2,y2)
    elif gameState.heLengths[bestEdgeHe] == 2:
        o = unsimpl.otherHe[bestEdgeHe]
        nxt = unsimpl.nextHe[o]
        x1,y1,x2,y2,_ = _heToCoords(nxt, vLeft, vRight, hUp, hDown)
        return _coords_to_move(x1,y1,x2,y2)
    else:
        x1,y1,x2,y2,_ = _heToCoords(bestEdgeHe, vLeft, vRight, hUp, hDown)
        return _coords_to_move(x1,y1,x2,y2)

# ----- Public entrypoint for the repo -----
def make_move(game_state: Dict) -> Tuple[int,int,str]:
    """
    Convert engine sets to JS-style boolean arrays, compute currentScore for the
    side to move, then call the JS-equivalent solver. If translation fails,
    fall back to a legal random move to avoid forfeits.
    """
    W, H = game_state["board_size"]  # boxes W×H => dots (W+1)×(H+1)
    # JS expects:
    #   vLines shape [W+1][H] where vLines[x][y] is the vertical at (col=x,row=y)
    #   hLines shape [H+1][W] where hLines[y][x] is the horizontal at (row=y,col=x)
    vLines = [[False for _ in range(H)] for _ in range(W + 1)]
    hLines = [[False for _ in range(W)] for _ in range(H + 1)]

    for (r, c) in game_state["vertical_lines"]:
        vLines[c][r] = True
    for (r, c) in game_state["horizontal_lines"]:
        hLines[r][c] = True

    you = game_state["your_player_id"]
    owners: Dict[Tuple[int,int], int] = game_state["box_owners"]
    my_boxes = sum(1 for v in owners.values() if v == you)
    opp_boxes = sum(1 for v in owners.values() if v and v != you)
    currentScore = my_boxes - opp_boxes

    try:
        mv = _consider(hLines, vLines, currentScore)
        # Defensive: ensure move is legal in engine terms
        if mv in game_state["available_moves"]:
            return mv
    except Exception:
        pass
    # Fallback to avoid invalid move forfeits
    return random.choice(list(game_state["available_moves"]))
