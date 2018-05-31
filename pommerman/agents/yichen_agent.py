"""Agents that can be run without using a Docker container. These are examples.
To use this with run_battle, include the following as an agent in the 'agents' flag, test::a.pommerman.agents.SimpleAgent. An example where all four agents use this SimpleAgent would be
python run_battle.py --agents=test::agents.YichenAgent,test::agents.SimpleAgent,test::agents.SimpleAgent,test::agents.SimpleAgent --config=PommeFFA-v0
python run_battle.py --agents=test::agents.YichenAgent,test::agents.DumbAgent,test::agents.DumbAgent,test::agents.DumbAgent --config=PommeFFA-v0
TODO:
1. kickable
2. when placing the bomb, consider the cases that one may get stucked 
3. if two agents wants to go to same directions, then try to find a path out
"""

from collections import defaultdict
import queue
import random
import copy
import numpy as np

from . import BaseAgent
from .. import constants
from .. import utility
from . import helper_func
from pommerman.characters import Flame


class YichenAgent(BaseAgent):
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

        if self.is_start():
            self._closest_safe_positions = () 
            self._prev_direction = []
            self._prev_position = []
        my_position = tuple(obs['position'])
        self.my_position = my_position
        board = np.array(obs['board'])
        self.board = board
        bombs = convert_bombs(np.array(obs['bomb_blast_strength']), np.array(obs['bomb_life']))
        self.bombs = bombs
        enemies = [constants.Item(e) for e in obs['enemies']]
        flames = convert_flames(board)
        ammo = int(obs['ammo'])
        blast_strength = int(obs['blast_strength']) 
        self.blast_strength = blast_strength
        items, dist, prev = self._djikstra(board, my_position, bombs, enemies, depth=10)
        dist_to_items, path_to_items = self.update_distance_to_items(items, dist, prev, board, enemies)
        self.prev = prev

        
        dist = dist_to_items 
        prev = path_to_items


        if my_position == self._closest_safe_positions: 
            self._closest_safe_positions = () 
        elif self._no_safe_position_step >= 4:
            self._no_safe_position_step = 0 
            self._closest_safe_positions = ()
        elif self._closest_safe_positions == (-1,-1):
            self._no_safe_position_step += 1
        
        if self._closest_safe_positions not in prev: 
            self._closest_safe_positions = ()

        if len(self._closest_safe_positions) != 0 and self._closest_safe_positions != (-1,-1): 
            direction = helper_func.get_next_direction_according_to_prev(my_position, self._closest_safe_positions, prev)
            helper_func.agent_output(["my_position {}, {}".format(my_position[0], my_position[1]),\
                                      "self._closest_safe_positions {}, {}".format(self._closest_safe_positions[0], self._closest_safe_positions[1]),\
                                      "No. 100: {}".format(direction)])
            
            
            
            if direction == self._prev_direction and self._prev_position == my_position: 
                self._closest_safe_positions = () 
                return constants.Action.Bomb.value
            elif direction is not None: 
                self._prev_direction = direction 
                self._prev_position = my_position
                return direction.value 
            else:
                self._closest_safe_positions = ()


        # Move if we are in an unsafe place. 2. move to safe places if possible
        unsafe_directions = self._directions_in_range_of_bomb(board, my_position, bombs, dist)
        if unsafe_directions:
            if len(self._closest_safe_positions) == 0: 
                self._closest_safe_positions = self._update_safe_position(bombs, board, my_position, items, dist, prev, enemies) 
                if self._closest_safe_positions == (-1,-1):
                    helper_func.agent_output(["Unsafe Directions", unsafe_directions,\
                                              my_position, self._closest_safe_positions,\
                                              "No. 201"])
                    directions = [constants.Action.Left, constants.Action.Right, constants.Action.Up, constants.Action.Down]
                    directions = self._filter_kicking_direction(board, my_position, directions, enemies)
                    self._no_safe_position_step = 1 
                    #directions += [constants.Action.Bomb]
                    rtn = random.choice(directions).value 
                    helper_func.agent_output([self._closest_safe_positions, \
                                            constants.Action(rtn)])
                    return rtn
                helper_func.agent_output(["PRE 200",
                                          self._closest_safe_positions,
                                          prev])
                direction = helper_func.get_next_direction_according_to_prev(my_position, self._closest_safe_positions, prev)
                
                helper_func.agent_output([board,"Unsafe Directions", unsafe_directions,\
                                         "next direction", direction, \
                                         "cloest safe place", self._closest_safe_positions, \
                                          "No. 200"])
                self._prev_direction = direction
                return direction
            #directions = self._find_safe_directions(board, my_position, unsafe_directions, bombs, enemies)
            #return random.choice(directions).value

        # Lay pomme if we are adjacent to an enemy.
        if self._is_adjacent_enemy(items, dist, enemies) and self._maybe_bomb(ammo, blast_strength, items, dist, my_position, board, prev, enemies):
            helper_func.agent_output(["No. 300"])
            return constants.Action.Bomb.value

        # Move towards an enemy if there is one in exactly three reachable spaces, randomly bomb if close.
        direction = self._near_enemy(my_position, items, dist, prev, enemies, 3)
        if direction is not None and (self._prev_direction != direction or random.random() < .5):
            directions = self._filter_unsafe_directions(board, my_position, [direction], bombs, items, dist, prev, enemies)
            if directions:
                self._prev_direction = direction
                helper_func.agent_output(["No. 400: {}".format(direction.value)])
                if random.random() < .2 and self._maybe_bomb(ammo, blast_strength, items, dist, my_position, board, prev, enemies): 
                    helper_func.agent_output(["No. 401"])
                    return constants.Action.Bomb.value
                return direction.value 

        # Move towards an enemy if there is one in exactly ten reachable spaces.
        direction = self._near_enemy(my_position, items, dist, prev, enemies, 10)
        if direction is not None and (self._prev_direction != direction or random.random() < .5): 
            directions = self._filter_unsafe_directions(board, my_position, [direction], bombs, items, dist, prev, enemies)
            if directions:
                self._prev_direction = direction
                helper_func.agent_output(["No. 410: {}".format(direction.value)])
                return direction.value 

        
        direction = self._near_negative_item(my_position, items, dist, prev, 2)
        # helper_func.agent_output(["NEGATIVE", direction], True)
        if direction is not None:
            if self._maybe_bomb(ammo, blast_strength, items, dist, my_position, board, prev, enemies):
                helper_func.agent_output(["No. 510"])
                return constants.Action.Bomb.value
            else:
                helper_func.agent_output(["No. 511"])
                return constants.Action.Stop.value

        # Move towards a good item if there is one within two reachable spaces.
        direction = self._near_item(my_position, items, dist, prev, 5)
        if direction is not None and self._prev_direction != direction:
            self._prev_direction = direction 
            directions = self._filter_unsafe_directions(board, my_position, [direction], bombs, items, dist, prev, enemies)
            if directions:
                helper_func.agent_output([direction.value, "No. 500"])
                return direction.value

        # Maybe lay a bomb if we are within a space of a wooden wall.
        if self._near_wood(my_position, items, dist, prev, 1):
            if self._maybe_bomb(ammo, blast_strength, items, dist, my_position, board, prev, enemies, "WOOD"):
                helper_func.agent_output(["No. 600"])
                return constants.Action.Bomb.value
            else:
                helper_func.agent_output(["No. 610: 0"], False)
                return constants.Action.Stop.value

        # Move towards a wooden wall if there is one within two reachable spaces and you have a bomb.
        direction = self._near_wood(my_position, items, dist, prev, 2)
        if direction is not None and obs['ammo'] != 0:
            directions = self._filter_unsafe_directions(board, my_position, [direction], bombs, items, dist, prev, enemies)
            if directions:
                helper_func.agent_output(["No. 700"]) 
                return directions[0].value

        # Choose a random but valid direction.
        directions = [constants.Action.Stop, constants.Action.Left, constants.Action.Right, constants.Action.Up, constants.Action.Down]
        valid_directions = self._filter_invalid_directions(board, my_position, directions, enemies)
        directions = self._filter_unsafe_directions(board, my_position, valid_directions, bombs, items, dist, prev, enemies)
        if random.random() < 0.75:
            directions = self._filter_recently_visited(directions, my_position, self._recently_visited_positions)
        if len(directions) > 1:
            directions = [k for k in directions if k != constants.Action.Stop]
        if not len(directions):
            directions = [constants.Action.Stop]

        # Add this position to the recently visited uninteresting positions so we don't return immediately.
        self._recently_visited_positions.append(my_position)
        self._recently_visited_positions = self._recently_visited_positions[-self._recently_visited_length:]

        rtn = random.choice(directions).value 
        helper_func.agent_output(["randomly choose value {}".format(rtn)], False)
        return rtn

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
        for r in range(max(0, mx - depth), min(13, mx + depth)):
            for c in range(max(0, my - depth), min(13, my + depth)):
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
                        if board[new_position[0], new_position[1]] == constants.Item.Skull.value:
                            new_val += 1

                        if new_val < dist[new_position]:
                            dist[new_position] = new_val
                            prev[new_position] = position 
                            Q.put((dist[new_position], new_position))
        return items, dist, prev 

    @classmethod
    def _directions_in_range_of_bomb(self, board, my_position, bombs, dist, bomb_ticking_threshold = 5, consider_bomb_life = True):
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
            path_bombable = helper_func.path_is_bombable(board, my_position, position)
            if path_bombable: 
                distance = helper_func.get_manhattan_distance(my_position, position)
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
        sorted_dist = sorted(sorted_dist, key=lambda position: dist[position]) 
        bomb_count = self.count_bomb_in_radius(my_position, bombs, items, radius=4)
        safe_positions = queue.PriorityQueue()
        for position in sorted_dist: 
            unsafe_directions = self._directions_in_range_of_bomb(board, position, bombs, dist, bomb_ticking_threshold=bomb_count * 2 + 5) 
            potential_unsafe_directions = self._directions_in_range_of_bomb(board, position, bombs, dist, bomb_ticking_threshold=bomb_count * 2 + 5, consider_bomb_life=False) 
            position_is_bad_corner = self.is_bad_corner(board, my_position, position, items, dist, prev, enemies, distance_to_enemies=3, threshold_wall_count = 2)


            if len(unsafe_directions) == 0 and not position_is_bad_corner and len(potential_unsafe_directions) == 0:
                helper_func.agent_output(["SAFE POSITION BOARD",
                                         position, my_position, board])
                return position
            elif len(unsafe_directions) == 0 and not position_is_bad_corner:
                safe_positions.put((dist[position] + len(potential_unsafe_directions) / 10.0, position))
            
        #append to safe position
        if not safe_positions.empty():
            return safe_positions.get()[1]
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
                if dist[position] == 1:
                    return True
        return False

    @staticmethod
    def _has_bomb(obs):
        return obs['ammo'] >= 1

    #@staticmethod
    def _maybe_bomb(self, ammo, blast_strength, items, dist, my_position, board, prev, enemies, scope="NOTHING"):
        """Returns whether we can safely bomb right now.

        Decides this based on:
        1. Do we have ammo?
        2. If we laid a bomb right now, will we be stuck?
        """
        # Do we have ammo?
        if ammo < 1:
            return False
        
        copy_bombs = copy.deepcopy(self.bombs)
        copy_bombs.append({'position': my_position, 'blast_strength': int(self.blast_strength), 'bomb_life': 25, 'moving_direction': None})
            
        # Will we be stuck?
        x, y = my_position
        for position in items.get(constants.Item.Passage):
            if dist[position] == np.inf or utility.position_is_agent(board,position) \
               or self._directions_in_range_of_bomb(board, position, copy_bombs, dist, consider_bomb_life=False) \
               or self.is_bad_corner(board, my_position, position, items, dist, prev, enemies, distance_to_enemies=3, threshold_wall_count = 3) \
               or self.susceptible_to_path_bombing(copy_bombs, my_position, position, dist, radius=4):
                continue

            # We can reach a passage that's outside of the bomb scope.
            px, py = position
            if px != x and py != y:
                return True 
            
            path_bombable = helper_func.path_is_bombable(board, my_position, position)
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

    @classmethod
    def _near_negative_item(cls, my_position, items, dist, prev, radius):
        objs = [constants.Item.Skull]
        nearest_item_position = cls._nearest_position(dist, objs, items, radius)
        return cls._get_direction_towards_position(my_position, nearest_item_position, prev)

    @staticmethod
    def _filter_invalid_directions(board, my_position, directions, enemies):
        ret = []
        for direction in directions:
            position = utility.get_next_position(my_position, direction)
            if utility.position_on_board(board, position) and utility.position_is_passable(board, position, enemies) and not helper_func.position_is_skull(board, position):
                ret.append(direction)
        return ret

    @staticmethod
    def _count_adjacent_walls(board, position, items, enemies):
        walls_count = 0 
        not_passible_items = items[constants.Item.Wood] + items[constants.Item.Rigid] + items[constants.Item.Bomb] 

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
            x, y = utility.get_next_position(my_position, direction)

            is_bad = False 
            unsafe_directions = self._directions_in_range_of_bomb(board, (x,y), bombs, dist) 
            is_bad_corner = self.is_bad_corner(board, my_position, (x,y), items, dist, prev, enemies, distance_to_enemies=-1, threshold_wall_count = 4)
            if len(unsafe_directions) != 0:
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

    def is_start(self): 
        return self.position == self.start_position and \
                    self.ammo == 1 and \
                    self.is_alive == True and \
                    self.blast_strength == constants.DEFAULT_BLAST_STRENGTH and \
                    self.can_kick == False 
    
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
            if dist[bomb['position']] < radius and helper_func.get_manhattan_distance(my_position, position) + radius + 1 > bomb['bomb_life']:
                return True
        return False

        
