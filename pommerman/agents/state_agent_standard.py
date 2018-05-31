"""State Machine Agent
TODO:
1. rewrite score function (flow map)
"""
from functools import partial

from pommerman.agents.score_func import score_func_with_target
from pommerman.agents.state_agent import StateAgent, State, win_cond_with_target
from . import helper_func
from . import mcts_inter_standard

class StateAgentStandard(StateAgent):
    """This is a baseline agent. After you can beat it, submit your agent to compete."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._mcts = mcts_inter_standard.MCTSAgentStandard()

    def AttackerAction(self):
        #============
        #PLACE BOMB IF NEAR ENEMY
        #============
        # Lay pomme if we are adjacent to an enemy.
        # if self._is_adjacent_enemy(self.items, self.dist, self.enemies) and self._maybe_bomb(self.ammo, self.blast_strength, self.items, self.dist, self.my_position, self.board, self.prev, self.enemies):
        #    helper_func.agent_output(["No. 300"])
        #    return constants.Action.Bomb.value

        #===========
        #MCTS TREE SEARCH IF NEAR ENEMY
        #===========
        actions_space = range(6)
        if self._target is not None:
            position = self.items.get(self._target,[])
            if not position or self.dist[position[0]] > 4:
                self._target = None
            else:
                #print("MCTS")
                #print(self.obs['board'], self.bombing_agents)
                return self._mcts.find_next_move(self.obs, actions_space, \
                                                 partial(win_cond_with_target, self._target), partial(score_func_with_target, self._target), self.bombing_agents);
        else:
            new_target = self._is_adjacent_enemy_target(self.items, self.dist, self.enemies)
            if new_target is not None:
                self._target = new_target
                #print("MCTS")
                #print(self.obs['board'],self.bombing_agents)
                return self._mcts.find_next_move(self.obs, actions_space, \
                                          partial(win_cond_with_target, self._target), partial(score_func_with_target, self._target), self.bombing_agents);
        
        #============
        #MOVE TOWARDS ENEMY
        #============
        enemy_detection_range = 6
        # Move towards an enemy if there is one in exactly ten reachable spaces
        direction = self._near_enemy(self.my_position, self.items, self.dist, self.prev, self.enemies, enemy_detection_range)
        if direction is not None: 
            directions = self._filter_unsafe_directions(self.board, self.my_position, [direction], self.bombs, self.items, self.dist, self.prev, self.enemies)
            if directions:
                self._prev_direction = direction
                helper_func.agent_output(["No. 400: {}".format(direction.value)])
                return direction.value

        #===========
        #STOP CAUSE NOT SAFE
        #===========
        return self.ExplorerAction()

