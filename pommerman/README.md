# Pommerman

### How to use the code:

* follow the docs/README.md to install related dependencies
* $ cd pommerman/cli
* First round FFA competition
  $ python run_battle.py --agents=test::agents.StateAgentExploit,test::agents.SimpleAgent,test::agents.SimpleAgent,test::agents.SimpleAgent --config=PommeFFACompetition-v0 --render
* Partially observable team mode (NIPS Competition)
  $ python run_battle.py --agents=test::agents.StateAgentExploit,test::agents.SimpleAgent,test::agents.SimpleAgent,test::agents.SimpleAgent --config=PommeTeamCompetition-v0 --render