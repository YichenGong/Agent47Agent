from collections import defaultdict
import queue
import random
import time
import numpy as np

from . import BaseAgent
from .. import constants
from .. import utility
from . import helper_func
from pommerman.characters import Flame

from pommerman import constants, agents

from pommerman.agents.gameNodes import game_node as gn

from datetime import datetime
import time

import copy
import math

class BFSAgent(BaseAgent):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.bombing_agents = {}

		self.copy_board = np.zeros((13,13))
		self.copy_walls = True
		self.level = 0
		self.num_of_nodes = 0

	def find_next_move(self, obs, action_space, win_condition, score_func, bombing_agents):

		self.action_space =  action_space
		self.win_condition = win_condition
		self.bombing_agents = bombing_agents
		self.score_func = score_func
		self.bombing_agents = bombing_agents

		my_pos = tuple(obs['position'])
		board = np.array(obs['board'])
		self.board = np.array(obs['board'])
		self._enemies = [constants.Item(e) for e in obs['enemies']]

		tree = gn.Tree(obs, True, self.bombing_agents)
		#get the root node
		self.rootNode = tree.get_root_node()
		
		#need way to find terminating condition
		self.end_time = 30
		start_time = time.time()
		elapsed = 0
		
		self.bfs(self.rootNode, start_time)

		# max_score = self.score_func(self.rootNode.get_child_with_max_score().state.obs)
		max_score = -1

		winner_node = None
		for child in self.rootNode.childArray:
			if(child.score) > max_score:
				max_score = child.score
				winner_node = child


		# print("max score {0} reached level {1} with move {2}".format(max_score, endLevel, winner_node.state.move))
		if winner_node is None:
			return constants.Action.Stop.value
		return (winner_node.state.move)
	
	def expand_node(self, promising_node):
		possible_states = promising_node.state.get_all_possible_states()
		for state in possible_states:
			new_node = gn.Node(state._obs, True, state.bombing_agents)
			new_node.set_state(state)
			new_node.bombing_agents = new_node.state.bombing_agents
			new_node.parent = promising_node
			new_node.increment_move_count(promising_node.get_move_count())
			new_node.my_move = state.move
			new_node.score = state.score
			promising_node.childArray.append(new_node)

	def bfs(self,nodeToExplore, start_time):
		nowTime = time.time()
		elapsed = (nowTime - start_time)
		parent = nodeToExplore
		Q = [parent]
		while (len(Q) != 0 and time.time() - nowTime <= 0.095):
			node = Q.pop(0)
			self.expand_node(node)
			# currLevel += 1
			for child in nodeToExplore.childArray:
				Q.append(child) 
				child.score = self.score_func(child.state._obs)
				parent = child
			
				while parent.parent != None:
					if parent.score > parent.parent.score:
						# parent.parent.state.set_score(self.score_func(parent.state.obs))
						parent.parent.score = parent.score
					parent = parent.parent

# random.seed(2)
# #board
# board = Board(7,7)
# board.init()
# list_of_moves = board.possible_moves_to_make.move_list
# print(list_of_moves)
# print(len(list_of_moves))
# #ids stuff
# level_counter = 1
# ids_ai = IDSAgent(level_counter)
# total_num_nodes = 0
# #time stuff
# elapsed = 0
# end_time = 60*5
# start_time = time.time()
# while(elapsed < end_time):
# 	move_and_score = ids_ai.find_next_move(board, 0, level_counter)
# 	level_counter += 1
# 	elapsed = time.time()-start_time
# 	print("Elasped time is: {0}".format(elapsed))
# 	print("Num of nodes looked at for depth {0} is {1}".format(level_counter-1, ids_ai.num_of_nodes))
# 	total_num_nodes += ids_ai.num_of_nodes
# print("IDS move is {0} with final score {1}".format(move_and_score[0], move_and_score[1]))
# print("Total nodes looked is {0}".format(total_num_nodes))