'''
python run_battle.py --agents=test::agents.MCTSAgent,test::agents.DummyAgent,test::agents.DummyAgent,test::agents.DummyAgent --config=PommeFFAFast-v0
python run_battle.py --agents=test::agents.MCTSAgent,test::agents.SimpleAgent,test::agents.SimpleAgent,test::agents.SimpleAgent --config=PommeFFAFast-v0
python run_battle.py --agents=test::agents.MCTSAgent,test::agents.SimpleAgent,test::agents.SimpleAgent,test::agents.SimpleAgent --config=PommeFFAFast-v0 --run_time=5 --render=True
python run_battle.py --agents=test::agents.MCTSAgent,test::agents.YichenAgent,test::agents.SimpleAgent,test::agents.SimpleAgent --config=PommeFFAFast-v0 --run_time=5 --render=True
'''
from pommerman.agents.mcts_inter import MCTSAgent


class MCTSAgentExplore(MCTSAgent):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	def UCB(self, the_node, child_win_score, child_visit_count, current_visit_count, best = False):

		 if child_visit_count == 0:#(the_node.childArray == []):
		 	return 100
		 else:

                         if best:
                                 return the_node.score / child_visit_count# + exploration
                         else:
                                 return current_visit_count / child_visit_count
	def set_expand_node_state(self, new_node):
                new_node.score = 0
                new_node.visit_count = 0
