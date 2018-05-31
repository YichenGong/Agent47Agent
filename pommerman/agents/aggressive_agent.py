from collections import defaultdict
import queue
import random

import numpy as np

from . import BaseAgent
from .. import constants
from .. import utility
from . import helper_func
from pommerman.characters import Flame


class AggressiveAgent(BaseAgent):

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

        my_position = tuple(obs['position'])
        self.my_position = my_position
        board = np.array(obs['board'])
        self.board = board
        #print(board)
        bombs = convert_bombs(np.array(obs['bomb_blast_strength']), np.array(obs['bomb_life']))
        self.bombs = bombs
        enemies = [constants.Item(e) for e in obs['enemies']]
        flames = convert_flames(board)
        ammo = int(obs['ammo'])
        #self.ammo = 100
        blast_strength = int(obs['blast_strength'])
        items, dist, prev = self._djikstra(board, my_position, bombs, enemies, depth=10)
        #print(prev)
        self.prev = prev
        #print(items)

        if my_position == self._closest_safe_positions: 
            self._closest_safe_positions = () 
        elif self._no_safe_position_step >= 3:
            self._no_safe_position_step = 0 
            self._closest_safe_positions = ()
        elif self._closest_safe_positions == (-1,-1):
            self._no_safe_position_step += 1
        # print(prev) 
        
        #print("CLOSEST SAFE POSITIONS", self._closest_safe_positions, " PREV", self.prev, " DIST", dist, " BOARD", board)

        # Move if we are in an unsafe place. 2. move to safe places if possible
        unsafe_directions = self._directions_in_range_of_bomb(board, my_position, bombs, dist)
        if unsafe_directions:
            if len(self._closest_safe_positions) == 0: 
                #print(board)
                self._closest_safe_positions = self._update_safe_position(bombs, dist, board, enemies) 
                if self._closest_safe_positions == (-1,-1):
                    self._no_safe_position_step = 1
                    return constants.Action.Stop.value 
                direction = helper_func.get_next_direction_according_to_prev(my_position, self._closest_safe_positions, prev).value
                self._prev_direction = direction
                return direction
            #directions = self._find_safe_directions(board, my_position, unsafe_directions, bombs, enemies)
            #return random.choice(directions).value

        #if len(self._closest_safe_positions) != 0 and self._closest_safe_positions != (-1,-1): 
        #    direction = helper_func.get_next_direction_according_to_prev(my_position, self._closest_safe_positions, prev)
        #    if direction is not None: 
        #        return direction.value

        # Lay pomme if we are adjacent to an enemy.
        if self._is_adjacent_enemy(items, dist, enemies) and self._maybe_bomb(ammo, blast_strength, items, dist, my_position, board):
            return constants.Action.Bomb.value

        # Move towards an enemy if there is one in exactly three reachable spaces
        direction = self._near_enemy(my_position, items, dist, prev, enemies, 3)
        if direction is not None and (self._prev_direction != direction or random.random() < .5):
            directions = self._filter_unsafe_directions(board, my_position, [direction], bombs, items, dist, prev, enemies)
            if directions:
                self._prev_direction = direction
                return direction.value    # random bomb

        # Aggressive agent: move towards enemy
        direction = self._near_enemy(my_position, items, dist, prev, enemies, 100)
        #print(direction)
        if direction is not None and (self._prev_direction != direction or random.random() < .5): 
            directions = self._filter_unsafe_directions(board, my_position, [direction], bombs, items, dist, prev, enemies)
            if directions:
                self._prev_direction = direction
                return direction.value 

        if self._near_negative_item(my_position, items, dist, prev, 4):
            if self._maybe_bomb(ammo, blast_strenght, items, dist, my_position, board):
                return utility.Action.Bomb.value
            else:
                return utility.Action.Stop.value

        # Aggressive agent: move towards a good item
        direction = self._near_item(my_position, items, dist, prev, 10)
        if direction is not None and self._prev_direction != direction:
            self._prev_direction = direction 
            directions = self._filter_unsafe_directions(board, my_position, [direction], bombs, items, dist, prev, enemies)
            if directions:
                return direction.value

        # Maybe lay a bomb if we are within a space of a wooden wall.
        if self._near_wood(my_position, items, dist, prev, 1):
            if self._maybe_bomb(ammo, blast_strength, items, dist, my_position, board):
                return constants.Action.Bomb.value
            else:
                return constants.Action.Stop.value

        # Aggressive agent: move towards a wall.
        direction = self._near_wood(my_position, items, dist, prev, 10)
        if direction is not None and obs['ammo'] != 0:
            directions = self._filter_unsafe_directions(board, my_position, [direction], bombs, items, dist, prev, enemies)
            if directions:
                return directions[0].value

        #Stop if no viable action
        rtn = constants.Action.Stop.value
        return rtn

        # Choose a random but valid direction.
#        directions = [constants.Action.Stop, constants.Action.Left, constants.Action.Right, constants.Action.Up, constants.Action.Down]
#        valid_directions = self._filter_invalid_directions(board, my_position, directions, enemies)
#        directions = self._filter_unsafe_directions(board, my_position, valid_directions, bombs, items, dist, prev, enemies)
#        if random.random() < 0.75:
#            directions = self._filter_recently_visited(directions, my_position, self._recently_visited_positions)
#        if len(directions) > 1:
#            directions = [k for k in directions if k != constants.Action.Stop]
#        if not len(directions):
#            directions = [constants.Action.Stop]

        # Add this position to the recently visited uninteresting positions so we don't return immediately.
#        self._recently_visited_positions.append(my_position)
#        self._recently_visited_positions = self._recently_visited_positions[-self._recently_visited_length:]

#        rtn = random.choice(directions).value 
#        helper_func.agent_output(["randomly choose value {}".format(rtn)])

    @staticmethod
    def _djikstra(board, my_position, bombs, enemies, depth=None, exclude=None):
        assert(depth is not None)
        #print(my_position)
        if exclude is None:
            exclude = [constants.Item.Fog, constants.Item.Rigid,
                       constants.Item.Skull, constants.Item.Flames]

        def out_of_range(p1, p2):
            x1, y1 = p1
            x2, y2 = p2
            return depth is not None and abs(y2 - y1) + abs(x2 - x1) > depth

        items = defaultdict(list)
        dist = {}
        prev = {}
        Q = queue.PriorityQueue()

        mx, my = my_position
        for r in range(max(0, mx - depth), min(13, mx + depth)):
            for c in range(max(0, my - depth), min(13, my + depth)):
                position = (r, c)
                if any([
                        out_of_range(my_position, position),
                        utility.position_in_items(board, position, exclude),
                ]):
                    continue

                if position == my_position:
                    dist[position] = 0
                else:
                    dist[position] = np.inf

                prev[position] = None
                Q.put((dist[position], position))

        for bomb in bombs:
            if bomb['position'] == my_position:
                items[constants.Item.Bomb].append(my_position)

        while not Q.empty():
            _, position = Q.get()

            if utility.position_is_passable(board, position, enemies):
                x, y = position
                val = dist[(x, y)] + 1
                for row, col in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    new_position = (row + x, col + y)
                    if new_position not in dist:
                        continue

                    new_val = val
                    #print(board[new_position[0], new_position[1]]
                    #Manually increase the distance to the skull
                    if board[new_position[0], new_position[1]] == constants.Item.Skull.value:
                        #print("LOLOLOL")
                        new_val += 3
                        print(new_val)

                    if new_val < dist[new_position]:
                        dist[new_position] = val
                        prev[new_position] = position

            item = constants.Item(board[position])
            items[item].append(position)
        #print(prev)
        return items, dist, prev

    def _directions_in_range_of_bomb(self, board, my_position, bombs, dist):
        ret = defaultdict(int)

        x, y = my_position
        for bomb in bombs:
            position = bomb['position']
            distance = dist.get(position)
            if distance is None:
                continue

            bomb_range = bomb['blast_strength']
            if distance > bomb_range:
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
            elif x == position[0]:
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


    def _update_safe_position(self, bombs, dist, board, enemies):

        sorted_dist = {k:v for  k, v in dist.items() if v < 15 and not helper_func.position_is_not_passible(board, k, enemies)}
        sorted_dist = sorted(sorted_dist, key=lambda position: dist[position]) 
        #print(sorted_dist)
        safe_positions = []
        for position in sorted_dist: 
            unsafe_directions = self._directions_in_range_of_bomb(None, position, bombs, dist) 
            #AVOID negative stuff on the path
            if len(unsafe_directions) == 0: 
            #     # find direction 
            #     direction = self._get_direction_towards_position(self.my_position, position, self.prev)
            #     # advance direction 
            #     x,y = utility.get_next_position(self.my_position, direction)
            #     # check if it has certain negative item 
            #     if board[x,y] == utility.Item.Skull:
            #         # if not, return position
            #         safe_positions.append(position)
            #     # elif utility.position_is_agent(board, position): 
            #     #     continue
            #     else:
                return position
        #append to safe position
        if len(safe_positions) > 0:
            return safe_positions[0]
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
    def _maybe_bomb(self, ammo, blast_strength, items, dist, my_position, board):
        """Returns whether we can safely bomb right now.

        Decides this based on:
        1. Do we have ammo?
        2. If we laid a bomb right now, will we be stuck?
        """
        # Do we have ammo?
        if ammo < 1:
            return False

        # Will we be stuck?
        x, y = my_position
        for position in items.get(constants.Item.Passage):
            #vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
            if dist[position] == np.inf or utility.position_is_agent(board,position) or self._directions_in_range_of_bomb(None, position, self.bombs, dist):
                continue

            # We can reach a passage that's outside of the bomb strength.
            if dist[position] > blast_strength:
                return True

            # We can reach a passage that's outside of the bomb scope.
            px, py = position
            if px != x and py != y:
                return True

        return False

    @staticmethod
    def _nearest_position(dist, objs, items, radius):
        nearest = None
        dist_to = max(dist.values())

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
    def _count_adjacent_walls(board, position, items):
        walls_count = 0
        for direction in [constants.Action.Up, constants.Action.Down, constants.Action.Left, constants.Action.Right]:
            new_pos = utility.get_next_position(position, direction)
            if not utility.position_on_board(board, new_pos) or \
               new_pos in items[constants.Item.Wood] + items[constants.Item.Rigid]:
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
        
        return false
        #    cls._get_direction_towards_position

    @classmethod
    def _filter_unsafe_directions(cls, board, my_position, directions, bombs, items, dist, prev, enemies):
        ret = []
        for direction in directions:
            x, y = utility.get_next_position(my_position, direction)
            is_bad = False
            for bomb in bombs:
                bx, by = bomb['position']
                blast_strength = bomb['blast_strength']
                if (x == bx and abs(by - y) <= blast_strength) or \
                   (y == by and abs(bx - x) <= blast_strength):
                    is_bad = True
                    break

            #MODIFIED
            #Check if the direction will place the player into a surrounded spot
            #If so, and the enemy is near, then the direction is not safe
            wall_count = cls._count_adjacent_walls(board, (x,y), items) 
            if wall_count == 3 and cls._near_enemy(my_position, items, dist, prev, enemies, 4):
                print(board)
                print("Corner Bad Direction!!", direction)
                is_bad = True
                break
            #elif 


            if not is_bad:
                ret.append(direction)
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
        # super().reset()
        # Agent().reset()
        return self.position == self.start_position and \
                    self.ammo == 1 and \
                    self.is_alive == True and \
                    self.blast_strength == constants.DEFAULT_BLAST_STRENGTH and \
                    self.can_kick == False
