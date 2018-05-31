'''
python run_battle.py --agents=test::agents.MCTSAgent,test::agents.DummyAgent,test::agents.DummyAgent,test::agents.DummyAgent --config=PommeFFAFast-v0
python run_battle.py --agents=test::agents.MCTSAgent,test::agents.SimpleAgent,test::agents.SimpleAgent,test::agents.SimpleAgent --config=PommeFFAFast-v0
python run_battle.py --agents=test::agents.MCTSAgent,test::agents.SimpleAgent,test::agents.SimpleAgent,test::agents.SimpleAgent --config=PommeFFAFast-v0 --run_time=5 --render=True
python run_battle.py --agents=test::agents.MCTSAgent,test::agents.YichenAgent,test::agents.SimpleAgent,test::agents.SimpleAgent --config=PommeFFAFast-v0 --run_time=5 --render=True
'''
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

class MCTSAgent(BaseAgent):
	level = 0

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.bombing_agents = {}

		self.copy_board = np.zeros((11,11))
		self.copy_walls = True

	def find_next_move(self, obs, action_space, win_condition, score_func, bombing_agents):
		#prep tuff
		self.win_condition = win_condition
		self.score_func = score_func
		self.bombing_agents = bombing_agents

		self.action_space =  action_space
		my_pos = tuple(obs['position'])
		board = np.array(obs['board'])
		self.board = np.array(obs['board'])
		self._enemies = [constants.Item(e) for e in obs['enemies']]

		if(self.copy_walls):
			self.copy_board[board == 1] = 9999

		self.copy_board [my_pos[0]] [my_pos[1]] += 1

		#check new bombs on field first
		bomb_life_map = np.array(obs['bomb_life'])
		
		# self.find_bombing_agents(bomb_life_map, board)

		#mcts stuff
		tree = gn.Tree(obs, True, self.bombing_agents)
		#get the root node
		self.rootNode = tree.get_root_node()
		
		#need way to find terminating condition
		self.end_time = 30
		start_time = time.time()
		elapsed = 0
		#while(elapsed < self.end_time):
		while (self.rootNode.visit_count < 250):
			promising_node = self.select_promising_node(self.rootNode)

			#expand that node
			#create the childs for that node
			if (promising_node == self.rootNode and self.rootNode.visit_count == 0):
			        self.expand_node(promising_node)
			
                        #Check if any immediate children from the root node satisfies winning condition
                        #If so, return that move directly
			if (promising_node == self.rootNode and self.rootNode.visit_count == 0):
                                winning_move = self.select_winning_move_from_root(promising_node)
                                if winning_move is not -1:
                                        if winning_move is constants.Action.Stop or winning_move is 5:
                                                return 5
                                        return winning_move.value                             
			if (promising_node == self.rootNode):
			        nodeToExplore = promising_node.get_random_child_node()                    
			else:
			        nodeToExplore = promising_node#promising_node.get_random_child_node()
			
			#simulate 
			simulationResult = self.simulate_random_play(nodeToExplore)
			
			#propogate up
			self.back_propogation(nodeToExplore,simulationResult)

			elapsed = time.time() - start_time
			if (elapsed >= 0.095):
                                #print("VISIT COUNT: ", self.rootNode.visit_count)
                                #print(obs['board'])
                                #for child in self.rootNode.childArray:
                                #        print(child.my_move ,child.score, child.visit_count, self.UCB(child, child.get_win_score(), child.get_visit_count(), self.rootNode.get_visit_count(), True))
                                break
			
		#winner is root node with child with big score
		#winner_node = rootNode.get_child_with_max_score()
		winner_node = None
		max_ucb = float('-inf')
		for child in self.rootNode.childArray:
			UCB1 = self.UCB(child, child.get_win_score(), child.get_visit_count(), self.rootNode.get_visit_count(), True)
			move = child.state.move
			if type(child.state.move) != int:
				move = child.state.move.value 
			if UCB1 > max_ucb and move in self.action_space:
				max_ucb = UCB1
				winner_node = child
		if not (winner_node is None):
			self.bombing_agents = winner_node.state.bombing_agents
			return winner_node.state.move
		else:
			return -1

	def UCB(self, the_node, child_win_score, child_visit_count, current_visit_count, best = False):
                raise NotImplementedError()

	def select_promising_node(self, rootNode):
		parentVisit = rootNode.visit_count

		#check for children
		if(rootNode.childArray == []):
			return rootNode

		best = 0
		best_node = None

		for child in rootNode.childArray:
			UCB1 = self.UCB(child, child.get_win_score(), child.get_visit_count(), self.rootNode.get_visit_count())
			if UCB1 > best or best_node == None:
				best = UCB1
				best_node = child

		# currentNode = rootNode
		# while currentNode.childArray != []:
		# 	best = 0
		# 	best_node = None
		# 	for child in currentNode.childArray:
		# 		UCB1 = self.UCB(child, child.get_win_score(), child.get_visit_count(), self.rootNode.get_visit_count())
		# 		if UCB1 > best or best_node == None:
		# 			best = UCB1
		# 			best_node = child
					
		# 	currentNode = best_node
			
		return best_node

	def expand_node(self, promising_node):

		#get the node
		#get the state from that node
		#say these are all the possible states I can go to?
		possible_states = promising_node.state.get_all_possible_states()
		for state in possible_states:
			new_node = gn.Node(state._obs, True, state.bombing_agents)
			new_node.set_state(state)
			new_node.bombing_agents = new_node.state.bombing_agents
			new_node.parent = promising_node
			new_node.increment_move_count(promising_node.get_move_count())
			new_node.my_move = state.move

                        #New Changes TO MCM
			#new_node.score = state.score
			self.set_expand_node_state(new_node)

			promising_node.childArray.append(new_node)

	def set_expand_node_state(self, new_node):
                raise NotImplementedError()

	def simulate_random_play(self, nodeToExplore):

		temp_copy = nodeToExplore.clone() #copy.deepcopy(nodeToExplore)
		temp_copy.state.score = 0
		state_won = False
		depth = random.randint(1,3)
		while (temp_copy.get_move_count() < depth):
			temp_copy.state.look_randomPlay()
			temp_copy.increment_move_count(temp_copy.get_move_count())
                        
			#temp_copy.state.score -= 10
			if(self.is_state_winner(temp_copy)):
                                #print("WINNING SHIT:\n", temp_copy.state._board)
                                state_won = True
                       	        break
                
		#print(temp_copy.my_move)
		if (state_won):
		        temp_copy.state.score = 100
		else:
		        temp_copy.state.score = self.score_func(temp_copy.state._obs)
		temp_copy.score = temp_copy.state.score

                #CHANGED FOR OPTIMIZATION
		#nodeToExplore.state.score = temp_copy.state.score
		#nodeToExplore.score = temp_copy.state.score

		nodeToExplore.state.score += temp_copy.state.score
		nodeToExplore.score += temp_copy.state.score
				
		nodeToExplore.visit_count += 1

		return temp_copy.state.score

	
	def back_propogation(self, nodeToExplore, score):
		parent = nodeToExplore
		
		while parent.parent != None:
			parent = parent.parent

			parent.visit_count += 1
			#parent.win_score += win
                
			parent.score += score

	def find_bombing_agents(self, bomb_life_map, board):
		
		#only add initial bombs
		locations = np.where(bomb_life_map == constants.DEFAULT_BOMB_LIFE-1)
		for r, c in zip(locations[0], locations[1]):
			b = board[r][c] - 10

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

	def is_state_winner(self, temp_node):
		return self.win_condition(temp_node.state._obs)

	def select_winning_move_from_root(self, rootNode):
                winning_move = -1
                for childNode in rootNode.childArray:
                        if self.is_state_winner(childNode):
                                winning_move = childNode.my_move
                                break
                return winning_move
