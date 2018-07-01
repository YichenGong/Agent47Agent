### To use this code

1. Follow docs/README.md to set up the environment
2. $ cd pommerman/cli 
3. if you want FFA mode:
     $ python run_battle.py --agents=test::agents.StateAgentExploit,test::agents.SimpleAgent,test::agents.SimpleAgent,test::agents.SimpleAgent --config=PommeFFAFast-v0
   if you want Team mode: 
     $ python run_battle.py --agents=test::agents.StateAgentExploit,test::agents.SimpleAgent,test::agents.SimpleAgent,test::agents.SimpleAgent --config=PommeTeamFast-v0 --render
     