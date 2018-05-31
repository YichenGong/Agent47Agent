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
from pommerman.characters import Flame

#================================
#FLOOD FILL WITH BOMB CHECKING
#===============================
def score_func_with_target(target, obs):
    def convert_bombs(strength_map, life_map):
        ret = []
        locations = np.where(strength_map > 0)
        for r, c in zip(locations[0], locations[1]):
            ret.append({'position': (r, c), 'blast_strength': int(strength_map[(r, c)]), 'bomb_life': int(life_map[(r, c)]), 'moving_direction': None})
        return ret

    #If we die, -100
    if obs['board'][obs['position']] not in\
       [constants.Item.Agent0.value, constants.Item.Agent1.value, constants.Item.Agent2.value, constants.Item.Agent3.value]:
        return -100

    #Check four directions of the target
    score = 0
    target_pos = np.where(obs['board'] == target.value)
    if target_pos[0]:
        target_pos = (target_pos[0][0], target_pos[1][0])
        directions_to_check = [constants.Action.Left, constants.Action.Right, constants.Action.Up, constants.Action.Down]
        bombs = convert_bombs(np.array(obs['bomb_blast_strength']), np.array(obs['bomb_life']))

        #Checking_range to limit search depth and calculate biggest possible area
        checking_range = 3
        frontier_positions = [target_pos]
        checked_positions = []

        total_area = 1
        passable_area = 0

        if not helper_func.check_if_in_bomb_range(obs['board'], bombs, target_pos):
            passable_area += 1

        for i in range(checking_range):
            total_area += 4 * (i+1)
            new_frontiers = []
            for front in frontier_positions:
                for direction in directions_to_check:
                    new_pos = utility.get_next_position(front, direction)
                    if new_pos not in checked_positions + frontier_positions and\
                       utility.position_on_board(obs['board'], new_pos) and\
                       obs['board'][new_pos] not in \
                       [constants.Item.Rigid.value, constants.Item.Wood.value, constants.Item.Bomb.value, constants.Item.Agent0.value, constants.Item.Agent1.value, constants.Item.Agent2.value, constants.Item.Agent3.value]:

                        new_frontiers.append(new_pos)
                        if not helper_func.check_if_in_bomb_range(obs['board'], bombs, new_pos):
                            passable_area += 1

            checked_positions = checked_positions + frontier_positions
            frontier_positions = new_frontiers

        score += 100 - (100 * passable_area / total_area)
    else:
        #Target is dead
        return 100

    # if the agent is close to its enemy, then the score goes up 
    tar, tac = obs['position'] # target agent row, target agent column 
    sar, sac = target_pos
    distance = abs(tar - sar) + abs(tac - sac)#(((tar - sar) ** 2 + (tac - sac) ** 2) ** 0.5 
    if distance != 0:
        score +=  (int)(25 / distance)   

    #print(passable_area, "/", total_area)
    #print("SCORE: \n",obs['board'], score)
    return score


#
#A SCORE FUNCTION THAT EVADES BOMBS
#
def score_func_evade(obs):
    def convert_bombs(strength_map, life_map):
        ret = []
        locations = np.where(strength_map > 0)
        for r, c in zip(locations[0], locations[1]):
            ret.append({'position': (r, c), 'blast_strength': int(strength_map[(r, c)]), 'bomb_life': int(life_map[(r, c)]), 'moving_direction': None})
        return ret

    #If we die, -100
    if obs['board'][obs['position']] not in\
       [constants.Item.Agent0.value, constants.Item.Agent1.value, constants.Item.Agent2.value, constants.Item.Agent3.value]:
        return -100
    
    position = obs['position']
    board = obs['board']
    bombs = convert_bombs(np.array(obs['bomb_blast_strength']), np.array(obs['bomb_life']))
    score = 100

    #Trace through bombs
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
        #If no in bomb direction
        else:
            continue

        #If bomb is right on me
        if direction is None:
            score -= 100

        #Trace from bomb to see if there's block in the way
        new_pos = b['position']
        while new_pos != position:
            new_pos = utility.get_next_position(new_pos, direction)
            if board[new_pos] in [constants.Item.Rigid.value, constants.Item.Wood.value, constants.Item.Flames.value]:
                break
        if new_pos == position and b['bomb_life'] < 10:
            score -= 25 * (11 - b['bomb_life']) / 10
    return score

#=====================================
#----MCTS search winning condition----
#----Target is the value of target----
#----Cond 1:--------------------------
#-----Target surrounded---------------
#-------------------------------------
#----Cond 2:--------------------------
#-----Target sur' by 2 bombs or walls-
#-----Cannot kick, but harder to win--
#=====================================
def win_cond_with_target(target, obs):
    #============
    #--win-cond--
    #============
    cond_num = 1
    if (cond_num == 1):
        board = np.array(obs['board'])
        coord = np.where(board == target.value)
        if not len(coord[0]):
            #Target Agent is dead, check if we're still alive
            return obs['board'][obs['position']] in [constants.Item.Agent0.value, constants.Item.Agent1.value, constants.Item.Agent2.value, constants.Item.Agent3.value]
            
        pos = (coord[0][0], coord[1][0])
        for direction in\
            [constants.Action.Up, constants.Action.Down, constants.Action.Left, constants.Action.Right]:

            new_pos = utility.get_next_position(pos, direction)

            if utility.position_on_board(board, new_pos) and \
               board[new_pos] not in \
               [constants.Item.Bomb.value, constants.Item.Rigid.value, constants.Item.Wood.value, constants.Item.Agent0.value, constants.Item.Agent1.value, constants.Item.Agent2.value, constants.Item.Agent3.value]:
                return False
                
        return True
    elif (cond_num == 2):
        print("Unknown Cond_Num")
        return False
    print("Unknown Cond_Num")
    return False

#Win if target is at location - used for traveling to safe position in evade
def win_if_arrive(target, obs):
    return obs['position'] == target


#
#A SCORE FUNCTION THAT CHECKS THE 4 DIRECTIONS OF THE AGENT
#
def score_func_with_target_FOUR(target, obs):
    #If we die, -100
    if obs['board'][obs['position']] not in\
       [constants.Item.Agent0.value, constants.Item.Agent1.value, constants.Item.Agent2.value, constants.Item.Agent3.value]:
        return -100

    #Check four directions of the target
    score = 0
    target_pos = np.where(obs['board'] == target.value)
    if target_pos[0]:
        target_pos = (target_pos[0][0], target_pos[1][0])
        directions_to_check = [constants.Action.Left, constants.Action.Right, constants.Action.Up, constants.Action.Down]

        checking_range = 4#obs['blast_strength'] 

        for direction in directions_to_check:
            new_pos = target_pos
            for j in range(checking_range):    
                new_pos = utility.get_next_position(new_pos, direction)
                if not utility.position_on_board(obs['board'], new_pos) or\
                   obs['board'][new_pos] in\
                   [constants.Item.Rigid.value, constants.Item.Wood.value]:#, constants.Item.Agent0.value, constants.Item.Agent1.value, constants.Item.Agent2.value, constants.Item.Agent3.value]: 
                    score += (int) (25 * (checking_range - j) / checking_range)
                    break
                if obs['board'][new_pos] == constants.Item.Bomb.value:
                    score += 25
                    break
    else:
        #Target is dead
        return 100

    # if the agent is close to its enemy, then the score goes up 
    tar, tac = obs['position'] # target agent row, target agent column 
    sar, sac = target_pos
    distance = abs(tar - sar) + abs(tac - sac)#(((tar - sar) ** 2 + (tac - sac) ** 2) ** 0.5 
    if distance != 0:
        score +=  (int)(25 / distance)                

    #print("SCORE: \n",obs['board'], score)
    return score

    #Check four directions of self
    self_pos = obs['position']
    directions_to_check = [constants.Action.Left, constants.Action.Right, constants.Action.Up, constants.Action.Down]
    
    checking_range = 4#obs['blast_strength'] 
    
    for direction in directions_to_check:
        new_pos = self_pos
        for j in range(checking_range):    
            new_pos = utility.get_next_position(new_pos, direction)
            if not utility.position_on_board(obs['board'], new_pos) or\
               obs['board'][new_pos] in\
               [constants.Item.Rigid.value, constants.Item.Wood.value, constants.Item.Agent0.value, constants.Item.Agent1.value, constants.Item.Agent2.value, constants.Item.Agent3.value]:
                score -= (int) (10 * (checking_range - j) / checking_range)
                break

            if obs['board'][new_pos] == constants.Item.Bomb.value:
                score -= 10
                break


    #print("SCORE: \n",obs['board'], score)
        
    return score
