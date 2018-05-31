'''
python run_battle.py --agents=test::agents.MCTSAgent,test::agents.DummyAgent,test::agents.DummyAgent,test::agents.DummyAgent --config=PommeFFAFast-v0
python run_battle.py --agents=test::agents.MCTSAgent,test::agents.SimpleAgent,test::agents.SimpleAgent,test::agents.SimpleAgent --config=PommeFFAFast-v0
python run_battle.py --agents=test::agents.MCTSAgent,test::agents.SimpleAgent,test::agents.SimpleAgent,test::agents.SimpleAgent --config=PommeFFAFast-v0 --run_time=5 --render=True
python run_battle.py --agents=test::agents.MCTSAgent,test::agents.YichenAgent,test::agents.SimpleAgent,test::agents.SimpleAgent --config=PommeFFAFast-v0 --run_time=5 --render=True
'''
from collections import defaultdict
import queue
import random
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

	def getRootNode_VisitCount(self):
		return self.rootNode.get_visit_count()

	def act(self, obs, action_space):
		self.action_space =  action_space
		my_pos = tuple(obs['position'])
		board = np.array(obs['board'])
		self.board = np.array(obs['board'])
		self._enemies = [constants.Item(e) for e in obs['enemies']]

		if(self.copy_walls):
			for i in range(len(self.copy_board)):
				for j in range(len(self.copy_board[i])):
					if (board[i][j] == 1):
						self.copy_board[i][j] = 9999

		
		self.copy_board [my_pos[0]] [my_pos[1]] += 1

		#check new bombs on field first
		bomb_life_map = np.array(obs['bomb_life'])
		
		self.find_bombing_agents(bomb_life_map, board)
		#print("bomb_life_map \n", bomb_life_map)
		#preform MCTS ONLY IF ENEMY AGENT IS VISISIBLE
		if self.enemy_in_my_sights_and_ammo(obs, 5):
			#print("my ammo",int(obs['ammo']))
			#print("HELLO MCTS")
			#check board, to see if someone inside my view made a bomb move			
			
			tree = gn.Tree(obs, True, self.bombing_agents)
			#get the root node
			self.rootNode = tree.get_root_node()
			
			#need way to find terminating condition
			self.end_time = 30
			start_time = time.time()
			elapsed = 0
			#while(elapsed < self.end_time):
			while (self.rootNode.visit_count < 25):
				#print("board \n",self.rootNode.state._board)
				#for i in self.rootNode.childArray:
					#print("ROOT NODES CHILDREN")
					#print("i move is",i.state.move)
					#print("i temp score is", i.state.score)
					#print("i temp node score is", i.score)

				
				promising_node = self.select_promising_node(self.rootNode)
				
				#print("promisng nodes move", promising_node.my_move)
				#print("promising nodes score", promising_node.score)

				#expand that node
				#create the childs for that node
				
				self.expand_node(promising_node)
				# print("EXPANDED PROMISE NODE")
				# for i in promising_node.childArray:
				# 	print("PROMISING NODES CHILDREN")
				# 	print("i move is",i.state.move)
				# 	print("i temp score is", i.state.score)
				# 	print("i temp node score is", i.score)
				# #explore that node
				# print("LENGTH OF CHILDREN", len(promising_node.childArray))
				nodeToExplore = promising_node.get_random_child_node()
				#print("Node to explore", nodeToExplore.state.move)
				#simulate 
				
				simulationResult = self.simulate_random_play(nodeToExplore)
				# simulationResult = self.simulate_random_play_yichen(nodeToExplore, self.copy_board)
				#propogate up
				self.back_propogation(nodeToExplore,simulationResult)
				nowTime = time.time()
				elapsed += (nowTime - start_time)
				start_time = nowTime
				# input()
			#winner is root node with child with big score
			#winner_node = rootNode.get_child_with_max_score()
			winner_node = None
			max_ucb = float('-inf')
			for child in self.rootNode.childArray:
				#print("child move is", child.state.move)
				#print ("the node", child.score)
				#print ("the node's state", child.state.score)
				UCB1 = self.UCB(child, child.get_win_score(), child.get_visit_count(), self.rootNode.get_visit_count())
				
				if UCB1 > max_ucb:
					max_ucb = UCB1
					winner_node = child
					#print("winning childs move is ", winner_node.state.move)
					#print("winning childs score is", winner_node.score)
					#print("UCB is", UCB1)
			
			self.bombing_agents = winner_node.state.bombing_agents
			
			#print("the move I make is",winner_node.state.move)
			#print("the move I picked score", winner_node.score)

			return winner_node.state.move

		#yichen agent time
		else: 
			#print("YICHEN AGENT TIME")
			

			self.agt = agents.YichenAgent()
			self.agt.make_a_visit_board(self.copy_board)
			aid = board[my_pos[0]][my_pos[1]]
			game_mode = constants.GameType.FFA
			position = my_pos
			self.agt.init_agent(aid, game_mode)
			self.agt.set_start_position(position)
			self.agt.reset(is_alive = True)

			r = self.agt.act(obs, action_space)
			#print (r)
			return r

	def UCB(self, the_node, child_win_score, child_visit_count, current_visit_count):
		if (the_node.childArray == []):
			return random.uniform(the_node.score- 15, the_node.score + 15)
		return the_node.score

                #DEPRECATE BELOW
		#UCB1 = (float(child_win_score)/float(child_visit_count)) + 1.414 * math.sqrt(2.0*math.log(current_visit_count)/float(child_visit_count))
		#return UCB1

	def select_promising_node(self, rootNode):
		parentVisit = rootNode.visit_count

		#check for children
		if(rootNode.childArray == []):
			return rootNode

		currentNode = rootNode

		while currentNode.childArray != []:
			#print("next level in tree")
			best = 0
			best_node = None
			#print("before for", len(currentNode.childArray))
			for child in currentNode.childArray:
				#check if child is dead
				#if dead, skip
				# if not child.state.am_I_alive():
				# 	#print("I am dead skip")
				# 	continue
				UCB1 = self.UCB(child, child.get_win_score(), child.get_visit_count(), self.rootNode.get_visit_count())
				#print ("UCB1", UCB1, "for", child.my_move)
				if UCB1 > best or best_node == None:
					best = UCB1
					best_node = child
					#print("best", best)
					#print("best_node", child.my_move, child.score)
				#print("best node with score", best_node.my_move, best_node.score)
			currentNode = best_node
			#print(type(currentNode.my_move))
			#print(type(currentNode.childArray))
			#print(len(currentNode.childArray))
			#if len(currentNode.childArray) > 0:
				#print(currentNode.childArray[0].my_move)

		return best_node

	def expand_node(self, promising_node):

		#IN TREE HELP WITH GETTING ALL POSSIBLE STATES 
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
			new_node.score = state.score
			promising_node.childArray.append(new_node)

	def simulate_random_play(self, nodeToExplore):

		temp_copy = nodeToExplore.clone() #copy.deepcopy(nodeToExplore)
		while (temp_copy.get_move_count() < 10):
			temp_copy.state.look_randomPlay()
			temp_copy.increment_move_count(temp_copy.get_move_count())
                
		temp_copy.state.score = temp_copy.state.get_score()
		temp_copy.score = temp_copy.state.score
		#print("score afer random play", temp_copy.state.score)
		nodeToExplore.state.score = temp_copy.state.score
		nodeToExplore.score = temp_copy.state.score
		nodeToExplore.visit_count += 1
		if temp_copy.state.is_winner():
			nodeToExplore.win_score = nodeToExplore.win_score + 1

		return temp_copy.state.score

	def simulate_random_play_yichen(self, nodeToExplore, visit_board):

		temp_copy = nodeToExplore.clone() #copy.deepcopy(nodeToExplore)
		
		#prep the yichen agent to play out 25 moves
		agt = agents.YichenAgent()
		temp_copy_board = visit_board
		agt.make_a_visit_board(temp_copy_board)
		my_pos = temp_copy.state._my_position
		aid = self.board[my_pos[0]][my_pos[1]]
		game_mode = constants.GameType.FFA
		agt.init_agent(aid, game_mode)
		agt.set_start_position(my_pos)
		agt.reset(is_alive = True)

		while (temp_copy.get_move_count() < 25):
			r = agt.act(temp_copy.state._obs, self.action_space)
			temp_copy.state.non_randomPlay(r)
			temp_copy.increment_move_count(temp_copy.get_move_count())
                
		temp_copy.state.score = temp_copy.state.get_score()
		temp_copy.score = temp_copy.state.score
		#print("score afer random play", temp_copy.state.score)
		nodeToExplore.state.score = temp_copy.state.score
		nodeToExplore.score = temp_copy.state.score
		nodeToExplore.visit_count += 1
		if temp_copy.state.is_winner():
			nodeToExplore.win_score = nodeToExplore.win_score + 1

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

	def enemy_in_my_sights_and_ammo(self, obs, r):

		if (int(obs['ammo']) == 0):
			return False

		search_up = True
		search_down = True
		search_left = True
		search_right = True

		my_pos = tuple(obs['position'])
		board = np.array(obs['board'])

		
		for radius in range(1, r):
			#vertical
			if search_up:
				check_pos = (my_pos[0]+radius, my_pos[1])
				if(check_pos[0] < 0 or check_pos[0] > 10):
					search_up = False
				else:
					#if (board[check_pos[0]][check_pos[1]] == 1 or board[check_pos[0]][check_pos[1]] == 2 or board[check_pos[0]][check_pos[1]] == 3):
					if not utility.position_is_passable(board, check_pos, self.enemies):
						search_up = False
					#if (board[check_pos[0]][check_pos[1]] == 11 or board[check_pos[0]][check_pos[1]] == 12 or board[check_pos[0]][check_pos[1]] == 13):
					if utility.position_is_enemy(board, check_pos, self.enemies):
						return True
			if search_down:
				check_pos = (my_pos[0]-radius, my_pos[1])
				if(check_pos[0] < 0 or check_pos[0] > 10):
					search_down = False
				else:
					#if (board[check_pos[0]][check_pos[1]] == 1 or board[check_pos[0]][check_pos[1]] == 2 or board[check_pos[0]][check_pos[1]] == 3):
					if not utility.position_is_passable(board, check_pos, self.enemies):
						search_down = False
					#if (board[check_pos[0]][check_pos[1]] == 11 or board[check_pos[0]][check_pos[1]] == 12 or board[check_pos[0]][check_pos[1]] == 13):
					if utility.position_is_enemy(board, check_pos, self.enemies):
						return True
			#horizontal
			if search_left:
				check_pos = (my_pos[0], my_pos[1]-radius)
				if(check_pos[1] < 0 or check_pos[1] > 10):
					search_left = False
				else:
					#if (board[check_pos[0]][check_pos[1]] == 1 or board[check_pos[0]][check_pos[1]] == 2 or board[check_pos[0]][check_pos[1]] == 3):
					if not utility.position_is_passable(board, check_pos, self.enemies):
						search_left = False
					#if (board[check_pos[0]][check_pos[1]] == 11 or board[check_pos[0]][check_pos[1]] == 12 or board[check_pos[0]][check_pos[1]] == 13):
					if utility.position_is_enemy(board, check_pos, self.enemies):
						return True
			if search_right:
				check_pos = (my_pos[0], my_pos[1]+radius)
				if(check_pos[1] < 0 or check_pos[1] > 10):
					search_right = False
				else:
					#if (board[check_pos[0]][check_pos[1]] == 1 or board[check_pos[0]][check_pos[1]] == 2 or board[check_pos[0]][check_pos[1]] == 3):
					if not utility.position_is_passable(board, check_pos, self.enemies):
						search_right = False
					#if (board[check_pos[0]][check_pos[1]] == 11 or board[check_pos[0]][check_pos[1]] == 12 or board[check_pos[0]][check_pos[1]] == 13):
					if utility.position_is_enemy(board, check_pos, self.enemies):
						return True
		return False