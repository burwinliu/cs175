# Todo, create a benchmark with already present Librarian Methods copied over to see performance and compare
#  (todo point 3) NOT WORKING YET BUT WILL BE CONTINUE TO PROGRESS ON THIS
import json
import time
from random import random

import matplotlib.pyplot as plt

from Requester import Requester

try:
    from malmo import MalmoPython
except ImportError:
    import MalmoPython


class BenchMark:
    def __init__(self, chests, failure):
        self.episode_number = 0
        self.obs_size = 10
        self._env_items = {'stone': 128, 'diamond': 64, 'glass': 64, 'ladder': 128, 'brick': 64, 'dragon_egg': 128 * 3}
        self.agent = MalmoPython.AgentHost()
        self._stochasticFailure = failure
        self._display = True
        self._sleep_interval = .2
        self.agent_position = 0


    def GetMissionXML(self):
        leftX = self.obs_size * 2 + 2
        front = f"<DrawCuboid x1='{leftX}' y1='0' z1='2' x2='-4' y2='10' z2='2' type='bookshelf' />"
        right = f"<DrawCuboid x1='-4' y1='0' z1='2' x2='-4' y2='10' z2='-10' type='bookshelf' />"
        left = f"<DrawCuboid x1='{leftX}' y1='0' z1='2' x2='{leftX}' y2='10' z2='-10' type='bookshelf' />"
        back = f"<DrawCuboid x1='{leftX}' y1='0' z1='-10' x2='-4' y2='10' z2='-10' type='bookshelf' />"
        floor = f"<DrawCuboid x1='{leftX}' y1='1' z1='-10' x2='-4' y2='1' z2='2' type='bookshelf' />"
        libraryEnv = front + right + left + back + floor
        item = f""
        for items in self._env_items:
            for x in range(self._env_items[items]):
                item += f"<DrawItem x='0' y='3' z='1' type='{items}' />"
        chests = f"<DrawBlock x='0' y='2' z='1' type='air' />" + \
                 f"<DrawBlock x='0' y='2' z='1' type='chest' />"
        for chest_num in range(self.obs_size):
            chests += f"<DrawBlock x='{chest_num * 2 + 2}' y='2' z='1' type='air' />"
            chests += f"<DrawBlock x='{chest_num * 2 + 2}' y='2' z='1' type='chest' />"
            chests += f"<DrawBlock x='{chest_num * 2 + 2}' y='1' z='0' type='diamond_block' />"
        chests += f"<DrawBlock x='0' y='2' z='1' type='chest' />"

        return f'''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
                        <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

                            <About>
                                <Summary>Librarian</Summary>
                            </About>

                            <ServerSection>
                                <ServerInitialConditions>
                                    <Time>
                                        <StartTime>12000</StartTime>
                                        <AllowPassageOfTime>false</AllowPassageOfTime>
                                    </Time>
                                    <Weather>clear</Weather>
                                </ServerInitialConditions>
                                <ServerHandlers>
                                    <FlatWorldGenerator generatorString="3;7,2;1;"/>
                                    <DrawingDecorator>
                                        {libraryEnv}
                                        {item}
                                        {chests}
                                        <DrawBlock x='-2' y='1' z='0' type='iron_block' />
                                        <DrawBlock x='0' y='1' z='0' type='emerald_block' />
                                    </DrawingDecorator>
                                    <ServerQuitWhenAnyAgentFinishes/>     
                                </ServerHandlers>
                            </ServerSection>

                            <AgentSection mode="Survival">
                                <Name>Librarian</Name>
                                <AgentStart>
                                    <Placement x="0.5" y="3" z="0.5" pitch="40" yaw="0"/>
                                    <Inventory>
                                    </Inventory>
                                </AgentStart>
                                <AgentHandlers>
                                    <ContinuousMovementCommands/>
                                    <DiscreteMovementCommands/>
                                    <ChatCommands/>
                                    <ObservationFromFullStats/>
                                    <InventoryCommands/>
                                    <ObservationFromFullInventory/>
                                    <ObservationFromRay/>
                                    <ObservationFromGrid>
                                        <Grid name="floorAll">
                                            <min x="-{int(self.obs_size / 2)}" y="-1" z="-{int(self.obs_size / 2)}"/>
                                            <max x="{int(self.obs_size / 2)}" y="0" z="{int(self.obs_size / 2)}"/>
                                        </Grid>
                                    </ObservationFromGrid>
                                    <AgentQuitFromTouchingBlockType>
                                        <Block type="iron_block"/>
                                    </AgentQuitFromReachingPosition>

                                </AgentHandlers>
                            </AgentSection>
                        </Mission>'''

    def init_malmo(self):
        """
        Initialize new malmo mission.
        """
        my_mission = MalmoPython.MissionSpec(self.GetMissionXML(), True)
        my_mission_record = MalmoPython.MissionRecordSpec()
        my_mission.requestVideo(800, 500)
        my_mission.setViewpoint(1)

        max_retries = 3
        my_clients = MalmoPython.ClientPool()
        my_clients.add(MalmoPython.ClientInfo('127.0.0.1', 10000))  # add Minecraft machines here as available

        for retry in range(max_retries):
            try:

                time.sleep(3)
                self.agent.startMission(my_mission, my_clients, my_mission_record, 0,
                                        'Librarian' + str(self.episode_number))
                break
            except RuntimeError as e:
                if retry == max_retries - 1:
                    print("Error starting mission:", e)
                    exit(1)
                else:
                    time.sleep(2)

        world_state = self.agent.getWorldState()
        while not world_state.has_mission_begun:
            time.sleep(0.1)
            world_state = self.agent.getWorldState()
            for error in world_state.errors:
                print("\nError:", error.text)

        return world_state

    def _optimal_retrieve(self, input: dict):
        """
            input: dict of objects to retrieve in format of {key: object_id, value: number to retrieve}
            Assumed that the self._itemPos is properly updated and kept done well
        """
        action_plan = []
        result = {}
        for item_id, num_retrieve in input.items():
            if len(self._itemPos[item_id]) > 0:
                # Therefore can retrieve, else you dun messed up
                pq_items = sorted([i for i in self._itemPos[item_id]])
                # Now we pop until we find
                while num_retrieve > 0 and len(pq_items) > 0:
                    toConsider = pq_items.pop()
                    if random() > self._stochasticFailure[toConsider]:
                        continue
                    chest = self._chestContents[toConsider]
                    if num_retrieve <= len(chest[item_id]):
                        toRetrieve = num_retrieve
                    else:
                        toRetrieve = len(chest[item_id])
                    action_plan.append((toConsider, item_id, toRetrieve))
                    if item_id not in result:
                        result[item_id] = 0
                    result[item_id] += toRetrieve
                    num_retrieve -= toRetrieve

        action_plan = sorted(action_plan, key=lambda x: x[0])  # Sort by the first elemetn in the tuple
        score = 0
        for position, item, num_retrieve in action_plan:
            # Should be in order from closest to furthest and retreiving the items so we should be able to execute
            #   from here
            score += self.moveToChest(position + 1)
            score += self.openChest()
            self.getItems({item: num_retrieve})
            score += self.closeChest()
        score += self.moveToChest(0)
        if self._display:
            score += self.openChest()
            # Max position item should be at
            for i in range(self._nextOpen):
                self.invAction("swap", i, i)
            score += self.closeChest()
        return result, score

    def _updateObs(self):
        toSleep = .1
        self.world_obs = None
        while self.world_obs is None:
            time.sleep(toSleep)
            toSleep += .2
            try:
                cur_state = self.agent.getWorldState()
                self.world_obs = json.loads(cur_state.observations[-1].text)
            except IndexError:
                print("retrying...")

    # Primative move actions
    def moveLeft(self, steps, force):
        if self._display or force:
            for i in range(steps):
                self.agent.sendCommand("moveeast")
                time.sleep(self._sleep_interval)
        return steps

    def moveRight(self, steps, force):
        if self._display or force:
            for i in range(steps):
                self.agent.sendCommand("movewest")
                time.sleep(self._sleep_interval)
        return steps

    def openChest(self):
        if self._display:
            self.agent.sendCommand("use 1")
            time.sleep(self._sleep_interval)
            self.agent.sendCommand("use 0")
            time.sleep(self._sleep_interval)
        return 1

    def closeChest(self):
        if self._display:
            for _ in range(10):
                self.agent.sendCommand("movenorth")
            time.sleep(self._sleep_interval)
            for _ in range(10):
                self.agent.sendCommand("movesouth")
            time.sleep(self._sleep_interval)
        return 1

    # Complex Move actions
    def moveToChest(self, chest_num, force=False):

        if self.agent_position == chest_num:
            return 0
        if self.agent_position - chest_num < 0:
            result = self.moveLeft(2 * abs(self.agent_position - chest_num), force)
        else:
            result = self.moveRight(2 * abs(self.agent_position - chest_num), force)
        self.agent_position = chest_num
        time.sleep(self._sleep_interval)
        return result

    def invAction(self, action, inv_index, chest_index):
        self._updateObs()
        if "inventoriesAvailable" in self.world_obs:
            chestName = self.world_obs["inventoriesAvailable"][-1]['name']
            self.agent.sendCommand(f"{action}InventoryItems {inv_index} {chestName}:{chest_index}")
            time.sleep(self._sleep_interval)
            self._updateObs()

    def getItems(self, query):
        """
            query = dict{ key = itemId: value = number to retrieve }
        """
        # TODO Fix this to fit with the Librarian Class
        chest = self._chestContents[self.agent_position - 1]
        for itemId, toRetrieve in query.items():
            for i in range(toRetrieve):
                try:
                    posToGet = chest[itemId].pop()
                except IndexError:
                    print("Bad retrieval, should not have happened, somewhere we did not update properly")
                    break
                # Create a new slot for this new item, and deposit there
                if itemId not in self._inventory:
                    self._inventory[itemId] = set()
                self._inventory[itemId].add(self._nextOpen)
                if self._display:
                    self.invAction("swap", self._nextOpen, posToGet)
                self._nextOpen += 1

                time.sleep(self._sleep_interval)
            # update if we have retrieved all said items within the chest
            if len(chest[itemId]) == 0:
                del self._chestContents[self.agent_position - 1][itemId]
                self._itemPos[itemId].remove(self.agent_position - 1)

    def log(self):
        plt.clf()
        plt.plot(self.returns[1:])
        plt.title('Librarian')
        plt.ylabel('Reward')
        plt.xlabel('Cycles')
        plt.savefig('rer.png')


if __name__ == "__main__":
    req = Requester(5, {'stone': 128, 'diamond': 64, 'glass': 64, 'ladder': 128, 'brick': 64, 'dragon_egg': 128 * 3}, 2)
    # Percentage for failure to open in a chest
    stochasticFailure = [0.35995969, 0.679561, 0.140505, 0.16909558, 0.969226, 0.62966605, 0.18746248, 0.90296069,
                         0.76486581, 0.90063654]
    for _ in range(10000):
        # TODO Average all inputs from requester, and distribute to correct chests
        chests = []
        pass

    for _ in range(50):
        mark = BenchMark(chests, stochasticFailure)
        mark.init_malmo()