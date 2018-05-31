"""Implementation of a simple deterministic agent using Docker."""
import os 
cwd = os.getcwd()
import sys
sys.path.append(cwd)
from pommerman import agents
from pommerman.runner import DockerAgentRunner


class MyAgent(DockerAgentRunner):
    def __init__(self):
        # self._agent = agents.SimpleAgent()
        
        self._agent = agents.state_agent_exploit.StateAgentExploit()

    def act(self, observation, action_space):
        return self._agent.act(observation, action_space)


def main():
    agent = MyAgent()
    agent.run()


if __name__ == "__main__":
    main()
