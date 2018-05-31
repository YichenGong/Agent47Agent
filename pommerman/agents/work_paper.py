


#           #directions = self._find_safe_directions(board, my_position, unsafe_directions, bombs, enemies)
            #return random.choice(directions).value

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#===================================================================================
#===============================RANDOM DIRECTION
#===================================================================================
        # Choose a random but valid direction.
        directions = [constants.Action.Stop, constants.Action.Left, constants.Action.Right, constants.Action.Up, constants.Action.Down]
        valid_directions = self._filter_invalid_directions(self.board, self.my_position, directions, self.enemies)
        directions = self._filter_unsafe_directions(self.board, self.my_position, valid_directions, self.bombs, self.items, self.dist, self.prev, self.enemies)
        if random.random() < 0.75:
            directions = self._filter_recently_visited(directions, self.my_position, self._recently_visited_positions)
        if len(directions) > 1:
            directions = [k for k in directions if k != constants.Action.Stop]
        if not len(directions):
            directions = [constants.Action.Stop]

        # Add this position to the recently visited uninteresting positions so we don't return immediately.
        self._recently_visited_positions.append(self.my_position)
        self._recently_visited_positions = self._recently_visited_positions[-self._recently_visited_length:]

        rtn = random.choice(directions).value 
        helper_func.agent_output(["randomly choose value {}".format(rtn)], True)
        return rtn        
