"""State Machine Agent
TODO:
1. rewrite score function (flow map)
"""

from collections import defaultdict
from functools import partial
from enum import Enum
import queue
import random
import copy
import numpy as np
import math

from . import BaseAgent
from .. import constants
from .. import utility
from . import helper_func
from pommerman.agents.score_func import score_func_with_target, score_func_evade, win_cond_with_target, win_if_arrive
from pommerman.characters import Flame

from . import mcts_inter_explore

class State(Enum):
    Evader = 0
    Explorer = 1
    Attacker = 2



class StateAgent(BaseAgent):
    """This is a baseline agent. After you can beat it, submit your agent to compete."""

    def __init__(self, *args, **kwargs):
        #super(SimpleAgent, self).__init__(*args, **kwargs)
        super().__init__(*args, **kwargs)

        # Keep track of recently visited uninteresting positions so that we don't keep visiting the same places.
        self._recently_visited_positions = []
        self._recently_visited_length = 6
        # Keep track of the previous direction to help with the enemy standoffs.
        self._prev_direction = None
        self._closest_safe_positions = ()
        self._no_safe_position_step = 0 
        self._prev_direction = []
        self._prev_position = []
        
        self._closest_safe_positions = () 
        self._prev_direction = []
        self._prev_position = []

        self._state = State.Explorer
        self._visit_map = np.zeros((11,11))
        self._target = None
        self.bombing_agents = {}
        self._evade_mcts = mcts_inter_explore.MCTSAgentExplore()

    def act(self, obs, action_space):
        def convert_bombs(strength_map, life_map):
            ret = []
            locations = np.where(strength_map > 0)
            for r, c in zip(locations[0], locations[1]):
                ret.append({'position': (r, c), 'blast_strength': int(strength_map[(r, c)]), 'bomb_life': int(life_map[(r, c)]), 'moving_direction': None})
            return ret
        def convert_flames(board):
            #Assuming that for each flame object, its life span is 2 ticks
            ret = []
            locations = np.where(board == 4)
            for r, c in zip(locations[0], locations[1]):
                ret.append(Flame((r, c)))
            return ret

        self.obs = obs
        self.my_position = tuple(obs['position'])
        self.board = np.array(obs['board'])
        self.bombs = convert_bombs(np.array(obs['bomb_blast_strength']), np.array(obs['bomb_life']))
        self.enemies = [constants.Item(e) for e in obs['enemies']]
        [self.blast_strength, self.ammo, self.flames] = [int(obs['blast_strength']), int(obs['ammo']), convert_flames(self.board)]
 
        [self.items, self.dist, self.prev] = self._djikstra(self.board, self.my_position, self.bombs, self.enemies, depth=15)
        [self.dist, self.prev] = self.update_distance_to_items(self.items, self.dist, self.prev, self.board, self.enemies)
        self.find_bombing_agents(np.array(obs['bomb_life']), self.board)

        if self.my_position == self._closest_safe_positions: 
            self._closest_safe_positions = () 
        elif self._no_safe_position_step >= 4:
            self._no_safe_position_step = 0 
            self._closest_safe_positions = ()
        elif self._closest_safe_positions == (-1,-1):
            self._no_safe_position_step += 1
        
        if self._closest_safe_positions not in self.prev: 
            self._closest_safe_positions = ()

#--------------------------------------
#========Visit Map Initialization==============
#--------------------------------------
        if self.is_start():
            self._closest_safe_positions = () 
            self._prev_direction = []
            self._prev_position = []
            self._state = State.Explorer
            for i in range(len(self._visit_map)):
                for j in range(len(self._visit_map[i])):
                    if (self.board[i][j] == 1):
                        self._visit_map[i][j] = 99999
                    else:
                        self._visit_map[i][j] = 0

#--------------------------------------
#=========Yichen Safe Direction========
#--------------------------------------
        
        if len(self._closest_safe_positions) != 0 and self._closest_safe_positions != (-1,-1): 
            direction = helper_func.get_next_direction_according_to_prev(self.my_position, self._closest_safe_positions, self.prev)
            helper_func.agent_output(["my_position {}, {}".format(self.my_position[0], self.my_position[1]),\
                                      "self._closest_safe_positions {}, {}".format(self._closest_safe_positions[0], self._closest_safe_positions[1]),\
                                      "No. 100: {}".format(direction)]) 
            
            
            if direction == self._prev_direction and self._prev_position == self.my_position: 
                self._closest_safe_positions = () 
                #print("Safe Bomb")
                return constants.Action.Bomb.value
            elif direction is not None: 

                #=======
                #If the next position to travel to is not safe, MCTS to survive
                #=======
                if helper_func.check_if_in_bomb_range_threshold(self.board, self.bombs,\
                                                                utility.get_next_position(self.my_position, direction)):
                    #print("safe MCTS: ", self.obs['can_kick'])
                    # actions_space = range(5)
                    directions = [constants.Action.Stop, constants.Action.Left, constants.Action.Right, constants.Action.Up, constants.Action.Down]
                    directions = self._filter_unsafe_directions(self.board, self.my_position, directions, self.bombs, self.items, self.dist, self.prev, self.enemies)
                    actions_space = [dir.value for dir in directions]
                    act =  self._evade_mcts.find_next_move(self.obs, actions_space, \
                                                           partial(win_if_arrive, self._closest_safe_positions), score_func_evade, self.bombing_agents)
                    helper_func.agent_output(["139 check bomb", self._closest_safe_positions, act], True)
                    act = act if type(act) == int else act.value
                    if act != -1:                        
                        return act

                self._prev_direction = direction 
                self._prev_position = self.my_position
                #print(self.board)
                #print("Safe prev direction", direction)
                print("146", direction.value)
                return direction.value 
            else:
                self._closest_safe_positions = ()
        
#--------------------------------------
#=============State Agent==============
#--------------------------------------
        [output, Att, Exp, Evd] = [constants.Action.Stop.value] + [-1] * 3
        if self.EvaderCondition(): 
            Evd = self.EvaderAction()
        elif self.AttackerCondition():
            Att = self.AttackerAction()
            print("ATTACK ACTION", Att)
            if Att == 5 and not self._maybe_bomb(self.ammo, self.blast_strength, self.items, self.dist, self.my_position, self.board, self.prev, self.enemies, self.bombs):
                #print("Not safe, Evade")
                Att = 0#self.EvaderAction()
            elif Att == -1:
                Att = self.ExplorerAction()
        elif self.ExplorerCondition():
            Exp = self.ExplorerAction()
        #print(self.board)
        #print(obs['bomb_life'])
        #print(self._closest_safe_positions)
        #print(Evd, Att, Exp)
        if Evd is not -1:
            output = Evd
            print("170 Evader ", output)
        elif Att is not -1:
            output = Att
            print("173 Attacker ", output)
        elif Exp is not -1:
            output = Exp
            print("176 Explorer", output)

        # output = self.bomb_if_towards_negative(output)
        if type(output) != int:
            return output.value
        return output

    def AttackerCondition(self):
        #return self._state is State.Attacker
        return self._state is State.Attacker or (self.ammo >= 1 and self._near_enemy(self.my_position, self.items, self.dist, self.prev, self.enemies, 5))

    def ExplorerCondition(self):
        return self._state is State.Explorer

    def EvaderCondition(self):
        self.unsafe_directions = self._directions_in_range_of_bomb(self.board, self.my_position, self.bombs, self.dist)
        return self.unsafe_directions

    def AttackerAction(self):
        raise NotImplementedError()

    def ExplorerAction(self):
        #============
        #BOMB NEGATIVE ITEM
        #============
        # bomb_count = self._near_bomb_item(self.my_position, self.items, self.dist, self.prev, 1)
        # bomb_count = self.count_bomb_in_radius(my_position, bombs, items, radius=4)
        # helper_func.agent_output(["NEGATIVE", bomb_count])
        # if bomb_count > 1:
        #     if self._maybe_bomb(self.ammo, self.blast_strength, self.items, self.dist, self.my_position, self.board, self.prev, self.enemies, self.bombs):
        #         helper_func.agent_output(["No. 510"])
        #         return constants.Action.Bomb.value

        #===========
        #MOVE TOWARDS GOOD ITEM
        #===========
        # Move towards a good item if there is one within eight reachable spaces.
        #directions = list(filter(lambda x: x != self._prev_direction,
        #helper_func.direction_to_items(self.my_position, self.items, self.dist, self.prev, 15)))
        directions =  helper_func.direction_to_items(self.my_position, self.items, self.dist, self.prev, 15)
        if directions is not None and len(directions) != 0:
            directions = self._filter_unsafe_directions(self.board, self.my_position, directions, self.bombs, self.items, self.dist, self.prev, self.enemies)
            if directions:
                helper_func.agent_output(["No. 500"])
                self._prev_direction = directions[0]
                return directions[0]

        #============
        #DESTROY WALL
        #============
        # Maybe lay a bomb if we are within a space of a wooden wall.
        directions_bombwood = directions_wood = helper_func.direction_to_woods(self.my_position, self.items, self.dist, self.prev, 1)
        if directions_bombwood:
            for d in directions_bombwood:
                new_pos = utility.get_next_position(self.my_position, d)
                if not helper_func.check_if_in_bomb_range(self.board, self.bombs, new_pos) and\
                   self._maybe_bomb(self.ammo, self.blast_strength, self.items, self.dist, self.my_position, self.board, self.prev, self.enemies, self.bombs, "WOOD"):

                    helper_func.agent_output(["No. 600"])
                    return constants.Action.Bomb.value
                else:
                    helper_func.agent_output(["No. 610: 0"])
                    return constants.Action.Stop.value

        #============
        #MOVE TOWARDS WOODS
        #============
        # Move towards wooden wallS  within five reachable spaces
        directions_wood = helper_func.direction_to_woods(self.my_position, self.items, self.dist, self.prev, 12)
        if directions_wood is not None or len(directions_wood) is not 0: # MOVE TOWARDS WOOD EVEN IF YOU DONT HAVE AMMO and self.ammo != 0:
            directions = self._filter_unsafe_directions(self.board, self.my_position, directions_wood, self.bombs, self.items, self.dist, self.prev, self.enemies)
            if directions:
                helper_func.agent_output(["No. 700"]) 
                return directions[0]

        #===========
        #MOVE TOWARDS UNFAMILIAR POSITION
        #===========
        # Choose a random but valid direction.
        directions = [constants.Action.Stop, constants.Action.Left, constants.Action.Right, constants.Action.Up, constants.Action.Down]
        valid_directions = self._filter_invalid_directions(self.board, self.my_position, directions, self.enemies)
        directions = self._filter_unsafe_directions(self.board, self.my_position, valid_directions, self.bombs, self.items, self.dist, self.prev, self.enemies)
        if random.random() < 0.75:
            directions = self._filter_recently_visited(directions, self.my_position, self._recently_visited_positions)
        if len(directions) > 1:
            directions = [k for k in directions if k != constants.Action.Stop]
        if not len(directions):
            directions = [constants.Action.Stop]

        # Add this position to the recently visited uninteresting positions so we don't return immediately.
        self._recently_visited_positions.append(self.my_position)
        self._recently_visited_positions = self._recently_visited_positions[-self._recently_visited_length:]

        #visit map update
        self._visit_map[self.my_position[0]][ self.my_position[1]] += 1

        #pick a dir with the smallest number
        values = []
        for d in directions:
            if d == constants.Action.Stop:
                values.append( (self._visit_map[self.my_position[0]][self.my_position[1]], d.value) )
            if d == constants.Action.Up:
                values.append( (self._visit_map[self.my_position[0]-1][self.my_position[1]], d.value) )
            if d == constants.Action.Down:
                values.append( (self._visit_map[self.my_position[0]+1][self.my_position[1]], d.value) )
            if d == constants.Action.Left:
                values.append( (self._visit_map[self.my_position[0]][self.my_position[1]-1], d.value) )
            if d == constants.Action.Right:
                values.append( (self._visit_map[self.my_position[0]] [self.my_position[1]+1], d.value) )
        rtn = min(values)
        helper_func.agent_output(["randomly choose value {}".format(rtn[1])])
 
        #If visit_map is has one number greater than 10, then switch to attacker mode
        #if ((self._visit_map > 10) & (self._visit_map != 99999)).any():
        #    print(self._visit_map)
        #    self._state = State.Attacker

        return rtn[1]

    def EvaderAction(self):
        #============
        #EVADING BOMB
        #============
        # Move if we are in an unsafe place. 2. move to safe places if possible
        self._closest_safe_positions = self._update_safe_position(self.bombs, self.board, self.my_position, self.items, self.dist, self.prev, self.enemies) 
        if self._closest_safe_positions == (-1,-1):
            helper_func.agent_output(["Unsafe Directions", self.unsafe_directions,\
                                      self.my_position, self._closest_safe_positions,\
                                      "No. 201"]) 
            directions = [constants.Action.Left, constants.Action.Right, constants.Action.Up, constants.Action.Down] 
            directions = self._filter_kicking_direction(self.board, self.my_position, directions, self.enemies)
            directions += [constants.Action.Stop]
            directions = self._filter_direction_toward_flames(self.board, self.my_position, directions, self.enemies)
            self._no_safe_position_step = 1             
            rtn = random.choice(directions).value 
            helper_func.agent_output(["308", self._closest_safe_positions, \
                                    constants.Action(rtn)], True)
            return rtn

            #MCTS to survive
            #return self._evade_mcts.find_next_move(self.obs, directions, \
            #                                     partial(win_if_arrive, self._closest_safe_positions), score_func_evade, self.bombing_agents);

            
        helper_func.agent_output(["PRE 200", self._closest_safe_positions, self.prev])
        direction = helper_func.get_next_direction_according_to_prev(self.my_position, self._closest_safe_positions, self.prev)
        helper_func.agent_output([self.board,"Unsafe Directions", self.unsafe_directions,\
                                  "next direction", direction, \
                                  "cloest safe place", self._closest_safe_positions, \
                                  "No. 200"], True)

        #=======
        #If the next position to travel to is not safe, MCTS to survive
        #=======
        # if helper_func.check_if_in_bomb_range_threshold(self.board, self.bombs,\
        #                                                 utility.get_next_position(self.my_position, direction)):
        #     #print(self.obs['bomb_life'])
        #     # actions_space = range(5)
        #     directions = [constants.Action.Stop, constants.Action.Left, constants.Action.Right, constants.Action.Up, constants.Action.Down]
        #     directions = self._filter_unsafe_directions(self.board, self.my_position, directions, self.bombs, self.items, self.dist, self.prev, self.enemies)
        #     helper_func.agent_output(["333",directions], True)
        #     actions_space = [dir.value for dir in directions]
        #     return self._evade_mcts.find_next_move(self.obs, actions_space, \
        #                                          partial(win_if_arrive, self._closest_safe_positions), score_func_evade, self.bombing_agents)


        self._prev_direction = direction
        return direction

    #place down bomb if going towards negative item
    # def bomb_if_towards_negative(self, direction):
    #     if direction in [constants.Action.Up, constants.Action.Down, constants.Action.Left, constants.Action.Right]\
    #        and self.board[utility.get_next_position(self.my_position, direction)] == constants.Item.Skull.value:
    #         return constants.Action.Bomb.value
    #     else:
    #         return direction
    
    def find_bombing_agents(self, bomb_life_map, board):
        #only add initial bombs
        locations = np.where(bomb_life_map == constants.DEFAULT_BOMB_LIFE-1)
        for r, c in zip(locations[0], locations[1]):
            b = board[r][c] - 11
            self.bombing_agents[(r,c)] = b

        #update kicked bombs
        #remove the older bombs
        keys_to_pop = []
        keys_to_add = []
        for key in self.bombing_agents.keys():
            if bomb_life_map[key[0]][key[1]] == 0: #or board[key[0]][key[1]] == 4:
                #check all directions
                #up
                r = key[0]-1
                c = key[1]
                if (r >= 0):
                    if bomb_life_map[r][c] > 0 and (r,c) not in self.bombing_agents.keys():
                        keys_to_add.append( ((r,c), self.bombing_agents[key]) )
                #down
                r = key[0]+1
                c = key[1]
                if (r < 11):
                    if bomb_life_map[r][c] > 0 and (r,c) not in self.bombing_agents.keys():
                        keys_to_add.append( ((r,c), self.bombing_agents[key]) )
                #left
                r = key[0]
                c = key[1]-1
                if (c >= 0):
                    if bomb_life_map[r][c] > 0 and (r,c) not in self.bombing_agents.keys():
                        keys_to_add.append( ((r,c), self.bombing_agents[key]) )
                #right
                r = key[0]
                c = key[1] + 1
                if (c < 11):
                    if bomb_life_map[r][c] > 0 and (r,c) not in self.bombing_agents.keys():
                        keys_to_add.append( ((r,c), self.bombing_agents[key]) )
                keys_to_pop.append((key[0],key[1]))
        for k in keys_to_pop:
            self.bombing_agents.pop(k, None)
        for k in keys_to_add:
            self.bombing_agents[k[0]] = k[1]
            #print(self.bombing_agents)
        # input("main mcts updating for kick")

#--------------------------------------
#======================================
#--------------------------------------

    @staticmethod
    def _djikstra(board, my_position, bombs, enemies, depth=None, exclude=None):
        assert(depth is not None)

        if exclude is None:
            exclude = [constants.Item.Fog]#, #constants.Item.Rigid,
                       #constants.Item.Flames] # SKULL

        def out_of_range(p1, p2):
            x1, y1 = p1
            x2, y2 = p2
            return depth is not None and abs(y2 - y1) + abs(x2 - x1) > depth

        items = defaultdict(list)
        dist = {}
        prev = {}
        Q = queue.PriorityQueue()
        Q.put([0, my_position])

        mx, my = my_position
        for r in range(max(0, mx - depth), min(11, mx + depth)):
            for c in range(max(0, my - depth), min(11, my + depth)):
                position = (r, c)
                
                if any([
                        out_of_range(my_position, position),
                        utility.position_in_items(board, position, exclude),
                ]):
                    continue

                
                dist[position] = np.inf

                prev[position] = None
                # Q.put((dist[position], position))
                item = constants.Item(board[position])
                items[item].append(position)
        dist[my_position] = 0

        for bomb in bombs:
            if bomb['position'] == my_position:
                items[constants.Item.Bomb].append(my_position)
        while not Q.empty():
            _, position = Q.get()
            x, y = position
            val = dist[(x, y)] + 1
            for row, col in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                new_position = (row + x, col + y) 
                if  utility.position_on_board(board, new_position):
                    if all([new_position in dist,
                        utility.position_is_passable(board, new_position, enemies)]):

                        new_val = val
                        #Manually increase the distance to the skull
                        # if board[new_position[0], new_position[1]] == constants.Item.Skull.value:
                        #     new_val += 4

                        if new_val < dist[new_position]:
                            dist[new_position] = new_val
                            prev[new_position] = position 
                            Q.put((dist[new_position], new_position))
        return items, dist, prev 

    @classmethod
    def _directions_in_range_of_bomb(self, board, my_position, bombs, dist, bomb_ticking_threshold = 15, consider_bomb_life = True):
        ret = defaultdict(int)

        x, y = my_position

        # BOMB connection
        for i in range(len(bombs)):
            for j in range(len(bombs)):
                if i == j:
                    continue
                bombs[i], bombs[j] = self._connect_bomb(bombs[i], bombs[j])

        for bomb in bombs:
            position = bomb['position'] 
            bomb_life = bomb['bomb_life']
            distance = dist.get(position)

            path_bombable = helper_func.path_is_bombable(board, my_position, position, bombs)
            if path_bombable: 
                distance = helper_func.get_manhattan_distance(my_position, position)

            if distance is None:
                continue

            if my_position == position:
                # We are on a bomb. All directions are in range of bomb.
                for direction in [
                    constants.Action.Right,
                    constants.Action.Left,
                    constants.Action.Up,
                    constants.Action.Down,
                ]:
                    ret[direction] = max(ret[direction], bomb['blast_strength'])

            bomb_range = bomb['blast_strength']

            if (distance > bomb_range and my_position != position and not path_bombable) \
                    or (bomb_life > distance + bomb_ticking_threshold and consider_bomb_life) :
                continue


            if x == position[0]:
                if y < position[1]:
                    # Bomb is right.
                    ret[constants.Action.Right] = max(ret[constants.Action.Right], bomb['blast_strength'])
                else:
                    # Bomb is left.
                    ret[constants.Action.Left] = max(ret[constants.Action.Left], bomb['blast_strength'])
            elif y == position[1]:
                if x < position[0]:
                    # Bomb is down.
                    ret[constants.Action.Down] = max(ret[constants.Action.Down], bomb['blast_strength'])
                else:
                    # Bomb is down.
                    ret[constants.Action.Up] = max(ret[constants.Action.Up], bomb['blast_strength'])
        return ret


    def _update_safe_position(self, bombs, board, my_position, items, dist, prev, enemies):

        sorted_dist = {k:v for  k, v in dist.items() if v < 15 and not helper_func.position_is_not_passible(board, k, enemies)}
        sorted_dist = sorted(sorted_dist, key=lambda position: dist[position]) #+ helper_func.get_manhattan_distance(my_position, position)) 
        # bomb_count = self.count_bomb_in_radius(my_position, bombs, items, radius=4)
        safe_positions = queue.PriorityQueue()
        best_dist = 99999
        for position in sorted_dist: 
            unsafe_directions = self._directions_in_range_of_bomb(board, position, bombs, dist, bomb_ticking_threshold=15)#bomb_count * 2 + 3) 
            # potential_unsafe_directions = self._directions_in_range_of_bomb(board, position, bombs, dist, bomb_ticking_threshold=15)#)bomb_count * 2 + 3, consider_bomb_life=False) 
            position_is_bad_corner = self.is_bad_corner(board, my_position, position, items, dist, prev, enemies, distance_to_enemies=3, threshold_wall_count = 2)
            

            if len(unsafe_directions) == 0 and not position_is_bad_corner: # and len(potential_unsafe_directions) == 0:
                # helper_func.agent_output(["SAFE POSITION BOARD",
                #                          position, my_position, board])
                if dist[position] <= best_dist:
                    best_dist = dist[position]
                    # calculate threat during escaping 
                    num_threats = 0 
                    curr_position = position
                    while prev[curr_position] != my_position: 
                        unsafe_dir = self._directions_in_range_of_bomb(board, curr_position, bombs, dist, bomb_ticking_threshold=15)
                        if len(unsafe_dir) != 0:
                            num_threats += 1
                        curr_position = prev[curr_position]
                    # append it to the queue 
                    safe_positions.put((num_threats, position))
                elif best_dist != 99999:
                    break
                # return position
            # elif len(unsafe_directions) == 0 and not position_is_bad_corner:
            #     safe_positions.put((dist[position] + len(unsafe_directions) / 10.0, position))
            
        #append to safe position
        if not safe_positions.empty():
            position = safe_positions.get()[1]
            helper_func.agent_output(["SAFE POSITION BOARD",
                                         position, my_position, board])
            return position
        else:
            # if there is no safe position, then
            return (-1,-1)   

    def _find_safe_directions(self, board, my_position, unsafe_directions, bombs, enemies):
        def is_stuck_direction(next_position, bomb_range, next_board, enemies):
            Q = queue.PriorityQueue()
            Q.put((0, next_position))
            seen = set()

            nx, ny = next_position
            is_stuck = True
            while not Q.empty():
                dist, position = Q.get()
                seen.add(position)
                
                px, py = position
                if nx != px and ny != py:
                    is_stuck = False
                    break

                if dist > bomb_range:
                    is_stuck = False
                    break

                for row, col in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    new_position = (row + px, col + py)
                    if new_position in seen:
                        continue
                    
                    if not utility.position_on_board(next_board, new_position):
                        continue

                    if not utility.position_is_passable(next_board, new_position, enemies):
                        continue
 
                    dist = abs(row + px - nx) + abs(col + py - ny)
                    Q.put((dist, new_position))
            return is_stuck

        # All directions are unsafe. Return a position that won't leave us locked.
        safe = []

        if len(unsafe_directions) == 4:
            next_board = board.copy()
            next_board[my_position] = constants.Item.Bomb.value

            for direction, bomb_range in unsafe_directions.items():
                next_position = utility.get_next_position(my_position, direction)
                nx, ny = next_position
                if not utility.position_on_board(next_board, next_position) or \
                   not utility.position_is_passable(next_board, next_position, enemies):
                    continue

                if not is_stuck_direction(next_position, bomb_range, next_board, enemies):
                    # We found a direction that works. The .items provided
                    # a small bit of randomness. So let's go with this one.
                    return [direction]
            if not safe:
                safe = [constants.Action.Stop]
            return safe

        x, y = my_position
        disallowed = [] # The directions that will go off the board.

        for row, col in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            position = (x + row, y + col)
            direction = utility.get_direction(my_position, position)

            # Don't include any direction that will go off of the board.
            if not utility.position_on_board(board, position):
                disallowed.append(direction)
                continue

            # Don't include any direction that we know is unsafe.
            if direction in unsafe_directions:
                continue

            if utility.position_is_passable(board, position, enemies) or utility.position_is_fog(board, position):
                safe.append(direction)

        if not safe:
            # We don't have any safe directions, so return something that is allowed.
            safe = [k for k in unsafe_directions if k not in disallowed]

        if not safe:
            # We don't have ANY directions. So return the stop choice.
            return [constants.Action.Stop]

        return safe

    @staticmethod
    def _is_adjacent_enemy(items, dist, enemies):
        for enemy in enemies:
            for position in items.get(enemy, []):
                if dist[position] <= 2:
                    return True
        return False

    @staticmethod
    #Return the enemy ID on board
    def _is_adjacent_enemy_target(items, dist, enemies):
        for enemy in enemies:
            for position in items.get(enemy, []):
                if dist[position] <= 3:
                    return enemy
        return None

    @staticmethod
    def _has_bomb(obs):
        return obs['ammo'] >= 1

    #@staticmethod
    def _maybe_bomb(self, ammo, blast_strength, items, dist, my_position, board, prev, enemies, bombs, scope="NOTHING"):
        """Returns whether we can safely bomb right now.

        Decides this based on:
        1. Do we have ammo?
        2. If we laid a bomb right now, will we be stuck?
        """
        # Do we have ammo?
        if ammo < 1:
            return False
        
        # if self.count_bomb_in_radius(my_position, bombs, items, 4) >= 3:
        #     return False 
        
        # if  self._directions_in_range_of_bomb(board, my_position, bombs, dist, consider_bomb_life=False): #current position connects other bombs
        #     return False

        copy_bombs = copy.deepcopy(self.bombs)
        copy_bombs.append({'position': my_position, 'blast_strength': int(self.blast_strength), 'bomb_life': 10, 'moving_direction': None})
        
        # Will we be stuck?
        x, y = my_position
        for position in items.get(constants.Item.Passage):
            if dist[position] > 5 or utility.position_is_agent(board,position) \
               or self._directions_in_range_of_bomb(board, position, copy_bombs, dist, consider_bomb_life=False) \
               or self.is_bad_corner(board, my_position, position, items, dist, prev, enemies, distance_to_enemies=3, threshold_wall_count = 3) \
               or self.susceptible_to_path_bombing(copy_bombs, my_position, position, dist, radius=4):
                continue

            # We can reach a passage that's outside of the bomb scope.
            px, py = position
            if px != x and py != y:
                return True 
            
            path_bombable = helper_func.path_is_bombable(board, my_position, position, bombs)
            if path_bombable:
                distance = helper_func.get_manhattan_distance(my_position, position)
            else:
                distance = dist[position]
            # We can reach a passage that's outside of the bomb strength. 
            if distance > blast_strength:
                return True

        return False

    @staticmethod
    def _nearest_position(dist, objs, items, radius):
        nearest = None
        # dist_to = max(dist.values())
        dist_to = 999999

        for obj in objs:
            for position in items.get(obj, []):
                d = dist[position]
                if d <= radius and d <= dist_to:
                    nearest = position
                    dist_to = d
        
        return nearest

    @staticmethod
    def _get_direction_towards_position(my_position, position, prev):
        if not position:
            return None

        next_position = position
        while prev[next_position] != my_position:
            next_position = prev[next_position]

        return utility.get_direction(my_position, next_position)

    @classmethod
    def _near_enemy(cls, my_position, items, dist, prev, enemies, radius):
        nearest_enemy_position = cls._nearest_position(dist, enemies, items, radius)
        return cls._get_direction_towards_position(my_position, nearest_enemy_position, prev)

    @classmethod
    def _near_good_powerup(cls, my_position, items, dist, prev, radius):
        objs = [
            constants.Item.ExtraBomb,
            constants.Item.IncrRange,
            constants.Item.Kick
        ]
        nearest_item_position = cls._nearest_position(dist, objs, items, radius)
        return cls._get_direction_towards_position(my_position, nearest_item_position, prev)

    @classmethod
    def _near_item(cls, my_position, items, dist, prev, radius):
        objs = [
            constants.Item.ExtraBomb,
            constants.Item.IncrRange,
            constants.Item.Kick
        ]
        nearest_item_position = cls._nearest_position(dist, objs, items, radius)
        return cls._get_direction_towards_position(my_position, nearest_item_position, prev)

    @classmethod
    def _near_wood(cls, my_position, items, dist, prev, radius):
        objs = [constants.Item.Wood]
        nearest_item_position = cls._nearest_position(dist, objs, items, radius)
        return cls._get_direction_towards_position(my_position, nearest_item_position, prev)

    def _near_bomb_item(self, my_position, items, dist, prev, radius):
        #objs = [constants.Item.Skull]
        #nearest_item_position = cls._nearest_position(dist, objs, items, radius)
        counter = 0
        directions = [constants.Action.Up, constants.Action.Down, constants.Action.Left, constants.Action.Right]
        for d in directions:
            new_pos = utility.get_next_position(my_position, d)
            if utility.position_on_board(self.board, new_pos) and\
               self.board[new_pos] == constants.Item.Bomb.value:
                        counter += 1
        return counter

    @staticmethod
    def _filter_invalid_directions(board, my_position, directions, enemies):
        ret = []
        for direction in directions:
            position = utility.get_next_position(my_position, direction)
            if utility.position_on_board(board, position) and utility.position_is_passable(board, position, enemies):# and not helper_func.position_is_skull(board, position):
                ret.append(direction)
        return ret

    @staticmethod
    def _count_adjacent_walls(board, position, items, enemies):
        walls_count = 0 
        not_passible_items = items[constants.Item.Wood] + items[constants.Item.Rigid] + items[constants.Item.Bomb] + items[constants.Item.Flames] 

        for enemy in enemies: 
            not_passible_items += items.get(enemy, [])

        
        
        for direction in [constants.Action.Up, constants.Action.Down, constants.Action.Left, constants.Action.Right]:
            new_pos = utility.get_next_position(position, direction)
            
            if not utility.position_on_board(board, new_pos) or \
               new_pos in not_passible_items:
                walls_count = walls_count + 1

        return walls_count

    @staticmethod
    def _check_enemy_near_hallway(board, my_position, new_position, enemies):
        def if_passable(pos):
            return not utility.position_on_board(board, pos)

        #check if it is a hallway
        pos_up = utility.get_next_position(new_position, constants.Action.Up)
        pos_down = utility.get_next_position(new_position, constants.Action.Down)
        pos_left = utility.get_next_position(new_position, constants.Action.Left)
        pos_right = utility.get_next_position(new_position, constants.Action.Right)
        #if if_passable(pos_up) and if_passable(pos_down):
            
        #elif if_passable(pos_left) and if_passable(pos_right):
        
        return False
        #    cls._get_direction_towards_position

    @classmethod
    def _filter_unsafe_directions(self, board, my_position, directions, bombs, items, dist, prev, enemies):
        ret = []
        bad_corner_surving_direction = []
        for direction in directions:
            if not utility.is_valid_direction(board, my_position, direction):
                continue
            x, y = utility.get_next_position(my_position, direction)

            is_bad = False 
            unsafe_directions = self._directions_in_range_of_bomb(board, (x,y), bombs, dist) 
            is_bad_corner = self.is_bad_corner(board, my_position, (x,y), items, dist, prev, enemies, distance_to_enemies=-1, threshold_wall_count = 4)
            if len(unsafe_directions) != 0:
                is_bad = True 
            
            if board[x,y] == constants.Item.Flames.value:
                is_bad = True
            
            if  is_bad_corner and not is_bad:
                is_bad = True 
                bad_corner_surving_direction.append(direction)

            if not is_bad:
                ret.append(direction) 
        if not ret: 
            return bad_corner_surving_direction
        else:
            return ret

    @staticmethod
    def _filter_recently_visited(directions, my_position, recently_visited_positions):
        ret = []
        for direction in directions:
            if not utility.get_next_position(my_position, direction) in recently_visited_positions:
                ret.append(direction)

        if not ret:
            ret = directions
        return ret

    def update_distance_to_items(self, items, dist, prev, board, enemies):
        distance_to_items = {}
        path_to_items = {}
        for item, values in items.items(): 
            for position in values:
                if utility.position_is_passable(board, position, enemies):
                    # if passable, then the distance to the item is same as the dist
                    distance_to_items[position] = dist[position]
                    path_to_items[position] = prev[position]
                else:
                    x, y = position
                    min_dist = np.inf 
                    for row, col in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        new_position = (row + x, col + y) 
                        
                        if  utility.position_on_board(board, new_position) and \
                            new_position in dist: 
                            if dist[new_position] + 1 < min_dist: 
                                min_dist = dist[new_position] + 1
                                path_to_items[position] = new_position
                    distance_to_items[position] = min_dist
        return distance_to_items, path_to_items  

    @classmethod
    def is_bad_corner(self, board, my_position, target_position, items, dist, prev, enemies, distance_to_enemies, threshold_wall_count=3):
        wall_count = self._count_adjacent_walls(board, target_position, items, enemies) 
        if distance_to_enemies == -1:
            if wall_count >= threshold_wall_count:
                return True 
            else:
                return False
        else:
            if wall_count >= threshold_wall_count and self._near_enemy(my_position, items, dist, prev, enemies, distance_to_enemies):
                return True 
            else:
                return False 

    @classmethod
    def _connect_bomb(self,bomb1, bomb2):
        position1 = bomb1['position']
        x1, y1 = position1
        bomb_life1 = bomb1['bomb_life'] 
        bomb_range1 = bomb1['blast_strength']

        position2 = bomb2['position']
        x2, y2 = position2
        bomb_life2 = bomb2['bomb_life'] 
        bomb_range2 = bomb2['blast_strength'] 

        bomb_connected = False
        if x1 == x2:
            bomb_dist = abs(y1 - y2)
            if bomb_dist < bomb_range1 + 1 or bomb_dist < bomb_range2 + 1: 
                bomb_connected = True                         
        elif y1 == y2:
            bomb_dist = abs(x1 - x2)
            if bomb_dist < bomb_range1 + 1 or bomb_dist < bomb_range2 + 1: 
                bomb_connected = True 
        if bomb_connected:
            min_bomb_life = min(bomb_life1, bomb_life2)
            bomb1['bomb_life'] = min_bomb_life 
            bomb2['bomb_life'] = min_bomb_life 
        
        return bomb1, bomb2 
    
    def count_bomb_in_radius(self, my_position, bombs, items, radius): 
        count = 0 
        for position in items.get(constants.Item.Bomb,[]):
            if helper_func.get_manhattan_distance(position, my_position) <= radius: 
                count += 1
        return count 
    
    
    @staticmethod
    def _filter_kicking_direction(board, my_position, directions, enemies):
        ret = []
        for direction in directions:
            position = utility.get_next_position(my_position, direction)
            if utility.position_on_board(board, position) and not utility.position_is_rigid(board, position):
                ret.append(direction)
        return ret 
    
    @staticmethod 
    def _filter_direction_toward_flames(board, my_position, directions, enemies):
        ret = []
        for direction in directions:
            position = utility.get_next_position(my_position, direction)
            if utility.position_on_board(board, position) and not utility.position_is_flames(board, position):
                ret.append(direction)
        return ret
    
    @classmethod 
    def susceptible_to_path_bombing(self, bombs, my_position, position, dist, radius=4):
        copy_bombs = copy.deepcopy(bombs)
        for i in range(len(copy_bombs)):
            for j in range(len(copy_bombs)):
                if i == j:
                    continue
                copy_bombs[i], copy_bombs[j] = self._connect_bomb(copy_bombs[i], copy_bombs[j]) 
        
        for bomb in copy_bombs: 
            if bomb['position'] not in dist:
                continue
            if dist[bomb['position']] < radius and helper_func.get_manhattan_distance(my_position, position) + radius > bomb['bomb_life']:
                return True
        return False

    def is_start(self): 
        
        # return self.my_position == self.start_position and \
        #     self.ammo == 1 and \
        #     self.is_alive == True and \
        #     self.blast_strength == constants.DEFAULT_BLAST_STRENGTH and \
        #     self.can_kick == False 
        return False
        
