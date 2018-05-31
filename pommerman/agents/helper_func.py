from pommerman import utility, constants

def position_is_not_passible(board, position, enemies):
    # return not any([utility.position_is_agent(board, position), utility.position_is_powerup(board, position) or utility.position_is_passage(board, position)]) and not utility.position_is_enemy(board, position, enemies)
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

# def position_is_skull(board, position):
#     return board[position] == constants.Item.Skull.value

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
            if utility.position_on_board(board, position) and utility.position_is_passable(board, position, enemies) and not helper_func.position_is_skull(board, position):
                ret.append(direction)
        return ret

        
