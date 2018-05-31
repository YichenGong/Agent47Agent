import os 
cwd = os.getcwd()
import sys
sys.path.append(cwd)
import pommerman
from pommerman import agents


def main():
    # Print all possible environments in the Pommerman registry
    print(pommerman.registry)

    # Create a set of agents (exactly four)
    agent_list = [
        agents.SimpleAgent(),
        agents.SimpleAgent(),
        agents.SimpleAgent(),
        # agents.RandomAgent(),
        agents.DockerAgent("pommerman/agent47agent", port=10080),
    ]
    # Make the "Free-For-All" environment using the agent list
    env = pommerman.make('PommeFFACompetition-v0', agent_list)

    # Run the episodes just like OpenAI Gym
    for i_episode in range(1):
        state = env.reset()
        done = False
        while not done:
            env.render()
            actions = env.act(state)
            state, reward, done, info = env.step(actions)
        print('Episode {} finished'.format(i_episode))
    env.close()


if __name__ == '__main__':
    main()
