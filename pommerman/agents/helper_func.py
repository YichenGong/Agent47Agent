from pommerman import utility, constants
from collections import defaultdict

def position_is_not_passible(board, position, enemies):
    return not utility.position_is_passable(board, position, enemies)

def get_next_direction_according_to_prev(my_position, target_position, prev): 
    cached_position = target_position
    if not cached_position: 
        
        return None 
    while prev[cached_position] != my_position: 
        
        cached_position = prev[cached_position] 
        if cached_position is None: 
            return None
    return utility.get_direction(my_position, cached_position)

# Change the default value for enabled to enable all output
def agent_output(output_array, enabled = 0):
    if(enabled):
        for s in output_array:
            print(s)

def position_is_flame(board, position):
    return utility._position_is_item(board, position, constants.Item.Flames)

def position_is_bombable(board, position, bombs): 
    return  any([utility.position_is_agent(board, position),
            utility.position_is_powerup(board, position),
            utility.position_is_passage(board, position),
            position_is_flame(board, position),
            position_is_bomb(bombs, position)])

def path_is_bombable(board, position1, position2, bombs):
    x1, y1 = position1 
    x2, y2 = position2 

    positions_to_determine = []
    if x1 == x2:
        if y1 <= y2:
            positions_to_determine = [(x1, yk) for yk in range(y1,y2+1)]
        else: 
            positions_to_determine = [(x1, yk) for yk in range(y2,y1+1)]
    elif y1 == y2: 
        if x1 <= x2: 
            positions_to_determine = [(xk, y1) for xk in range(x1,x2+1)]
        else: 
            positions_to_determine = [(xk, y1) for xk in range(x2,x1+1)]
    else:
        return False 
    return all([position_is_bombable(board, p, bombs) for p in positions_to_determine])

def position_is_bomb(bombs, position):
    """Check if a given position is a bomb.
    
    We don't check the board because that is an unreliable source. An agent
    may be obscuring the bomb on the board.
    """
    for bomb in bombs:
        if position == bomb["position"]:
            return True
    return False

def get_manhattan_distance(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

#==============================
#------STATE AGENT HELPER------
#==============================

#Get all positions of objects within a certain radius
def objects_within_radius(dist, objs, items, radius):
    obj_pos = []
    # dist_to = max(dist.values())
    dist_to = 999999
    
    for obj in objs:
        for position in items.get(obj, []):
            d = dist[position]
            if d <= radius:
                if d < dist_to:
                    obj_pos.insert(0, position)
                    dist_to = d
                else:
                    obj_pos.append(position)
        
    return obj_pos

#Get all wood positions and then returns directions towards them (array)
def direction_to_items(my_position, items, dist, prev, radius):
    objs = [constants.Item.ExtraBomb,
            constants.Item.IncrRange,
            constants.Item.Kick]
    item_positions = objects_within_radius(dist, objs, items, radius)
    directions = []
    for pos in item_positions:
        d = get_next_direction_according_to_prev(my_position, pos, prev)
        if d not in directions:
            directions.append(d)
    return directions

#Get all wood positions and then returns directions towards them (array)
def direction_to_woods(my_position, items, dist, prev, radius):
    objs = [constants.Item.Wood]
    item_positions = objects_within_radius(dist, objs, items, radius)
    directions = []
    for pos in item_positions:
        d = get_next_direction_according_to_prev(my_position, pos, prev)
        if d not in directions:
            directions.append(d)
    return directions

#Check if the position is in the range of bomb
def check_if_in_bomb_range(board, bombs, position):
    for b in bombs:
        #Set the direction to trace
        direction = None
        if (b['position'][0] == position[0] and abs(b['position'][1] - position[1]) <= b['blast_strength']):
            if b['position'][1] < position[1]:
                direction = constants.Action.Right
            elif b['position'][1] > position[1]:
                direction = constants.Action.Left
        elif(b['position'][1] == position[1] and abs(b['position'][0] - position[0]) <= b['blast_strength']):
            if b['position'][0] < position[0]:
                direction = constants.Action.Down
            elif b['position'][0] > position[0]:
                direction = constants.Action.Up
        else:
            continue

        if direction is None:
            return True

        #Trace from bomb to see if there's block in the way
        new_pos = b['position']
        while new_pos != position:
            new_pos = utility.get_next_position(new_pos, direction)
            if board[new_pos] in [constants.Item.Rigid.value, constants.Item.Wood.value]:
                break
        if new_pos == position:
            return True
    return False

#Check if the position is in the range of bomb
def check_if_in_bomb_range_threshold(board, bombs, position, threshold = 15):
    for b in bombs:
        if (b['bomb_life'] > threshold):
            continue

        #Set the direction to trace
        direction = None
        if (b['position'][0] == position[0] and abs(b['position'][1] - position[1]) <= b['blast_strength']):
            if b['position'][1] < position[1]:
                direction = constants.Action.Right
            elif b['position'][1] > position[1]:
                direction = constants.Action.Left
        elif(b['position'][1] == position[1] and abs(b['position'][0] - position[0]) <= b['blast_strength']):
            if b['position'][0] < position[0]:
                direction = constants.Action.Down
            elif b['position'][0] > position[0]:
                direction = constants.Action.Up
        else:
            continue

        if direction is None:
            return True

        #Trace from bomb to see if there's block in the way
        new_pos = b['position']
        while new_pos != position:
            new_pos = utility.get_next_position(new_pos, direction)
            if board[new_pos] in [constants.Item.Rigid.value, constants.Item.Wood.value]:
                break
        if new_pos == position:
            return True
    return False

def _filter_invalid_directions(board, my_position, directions, enemies):
        ret = []
        for direction in directions:
            position = utility.get_next_position(my_position, direction)
            if utility.position_on_board(board, position) and utility.position_is_passable(board, position, enemies) and not position_is_skull(board, position):
                ret.append(direction)
        return ret

        
def _directions_in_range_of_bomb(board, my_position, bombs, dist, bomb_ticking_threshold = 15, consider_bomb_life = True):
    ret = defaultdict(int)

    x, y = my_position

    # BOMB connection
    for i in range(len(bombs)):
        for j in range(len(bombs)):
            if i == j:
                continue
            bombs[i], bombs[j] = _connect_bomb(bombs[i], bombs[j])

    for bomb in bombs:
        position = bomb['position'] 
        bomb_life = bomb['bomb_life']
        distance = dist.get(position)

        path_bombable = path_is_bombable(board, my_position, position, bombs)
        if path_bombable: 
            distance = get_manhattan_distance(my_position, position)

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

def _connect_bomb(bomb1, bomb2):
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

def is_bad_corner(board, my_position, target_position, items, dist, prev, enemies, distance_to_enemies, threshold_wall_count=3):
    wall_count = _count_adjacent_walls(board, target_position, items, enemies) 
    if distance_to_enemies == -1:
        if wall_count >= threshold_wall_count:
            return True 
        else:
            return False
    else:
        if wall_count >= threshold_wall_count and _near_enemy(my_position, items, dist, prev, enemies, distance_to_enemies):
            return True 
        else:
            return False 

def _near_enemy(my_position, items, dist, prev, enemies, radius):
    nearest_enemy_position = _nearest_position(dist, enemies, items, radius)
    return get_next_direction_according_to_prev(my_position, nearest_enemy_position, prev)

def _nearest_position(dist, objs, items, radius):
    nearest = None
    
    dist_to = 999999

    for obj in objs:
        for position in items.get(obj, []):
            d = dist[position]
            if d <= radius and d <= dist_to:
                nearest = position
                dist_to = d
    
    return nearest


def _near_good_powerup(my_position, items, dist, prev, radius):
    objs = [
        constants.Item.ExtraBomb,
        constants.Item.IncrRange,
        constants.Item.Kick
    ]
    nearest_item_position = _nearest_position(dist, objs, items, radius)
    return helper_func.get_next_direction_according_to_prev(my_position, nearest_item_position, prev) 


def _near_item(my_position, items, dist, prev, radius):
    objs = [
        constants.Item.ExtraBomb,
        constants.Item.IncrRange,
        constants.Item.Kick
    ]
    nearest_item_position = _nearest_position(dist, objs, items, radius)
    return get_next_direction_according_to_prev(my_position, nearest_item_position, prev) 


def count_bomb_in_radius(my_position, bombs, items, radius): 
        count = 0 
        for position in items.get(constants.Item.Bomb,[]):
            if helper_func.get_manhattan_distance(position, my_position) <= radius: 
                count += 1
        return count 


def _filter_direction_toward_flames(board, my_position, directions, enemies):
    ret = []
    for direction in directions:
        position = utility.get_next_position(my_position, direction)
        if utility.position_on_board(board, position) and not utility.position_is_flames(board, position):
            ret.append(direction)
    return ret