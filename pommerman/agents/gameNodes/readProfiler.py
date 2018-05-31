import pstats

p = pstats.Stats("creating_node.txt")
p.sort_stats('cumtime').print_stats(100)
p = pstats.Stats("creating_node_and_forward.txt")
p.sort_stats('cumtime').print_stats(100)

p = pstats.Stats("creating_node_and_clone.txt")
p.sort_stats('cumtime').print_stats(100)
# p = pstats.Stats("386_rand_trail_fast_2.0.txt")
# p.sort_stats('tottime').print_stats(5)

# p = pstats.Stats("704_rand_trail_fast.txt")
# p.sort_stats('tottime').print_stats(5)
# p = pstats.Stats("704_rand_trail_fast_2.0.txt")
# p.sort_stats('tottime').print_stats(5)

# p = pstats.Stats("890_rand_trail_fast.txt")
# p.sort_stats('tottime').print_stats(5)
# p = pstats.Stats("890_rand_trail_fast_2.0.txt")
# p.sort_stats('tottime').print_stats(5)

# p = pstats.Stats("204_rand_trail_fast.txt")
# p.sort_stats('tottime').print_stats(5)
# p = pstats.Stats("204_rand_trail_fast_2.0.txt")
# p.sort_stats('tottime').print_stats(5)

# p = pstats.Stats("65_rand_trail_fast.txt")
# p.sort_stats('tottime').print_stats(5)
# p = pstats.Stats("65_rand_trail_fast_2.0.txt")
# p.sort_stats('tottime').print_stats(5)

# print("original")
# p = pstats.Stats("rand_trail_" + str(73) + "_original.txt")
# p.sort_stats('cumtime').print_stats(5)
# print ("updated")
# p = pstats.Stats("rand_trail_" + str(73) + "_updated.txt")
# p.sort_stats('cumtime').print_stats(5)

# print("post bug seed 73")
# p = pstats.Stats("rand_trail_" + str(73) + "_bug_fixed.txt")
# p.sort_stats('tottime').print_stats(10)

# print("post bug comp restart seed 73")
# p = pstats.Stats("rand_trail_" + str(73) + "_bug_comp_restart.txt")
# p.sort_stats('tottime').print_stats(20)

# print("alot refactor seed 73")
# p = pstats.Stats("rand_trail_" + str(73) + "_alot_refactor.txt")
# p.sort_stats('tottime').print_stats(10)

# print("even more refactor bug seed 73")
# p = pstats.Stats("rand_trail_" + str(73) + "_alot_refactor_2.txt")
# p.sort_stats('tottime').print_stats(10)

# print("even more refactor bug seed 73, brought back find_intersection")
# p = pstats.Stats("rand_trail_" + str(73) + "_alot_refactor_3.txt")
# p.sort_stats('tottime').print_stats(10)

# print("even more refactor bug seed 73, brought back get_possible_moves is annoying")
# p = pstats.Stats("rand_trail_" + str(73) + "_alot_refactor_4.txt")
# p.sort_stats('tottime').print_stats(10)

# print("even more refactor fill_board_two sped up")
# p = pstats.Stats("rand_trail_" + str(73) + "_alot_refactor_fill_board_two.txt")
# p.sort_stats('tottime').print_stats(10)

# print("even more refactor get_possible_moves sped up")
# p = pstats.Stats("rand_trail_" + str(73) + "_alot_hard_code_get_possible_moves.txt")
# p.sort_stats('tottime').print_stats(10)

# print("even more refactor get_possible_moves_2 sped up")
# p = pstats.Stats("rand_trail_" + str(73) + "_alot_hard_code_get_possible_moves_2.txt")
# p.sort_stats('tottime').print_stats(10)

# print("Tuesday 1")
# p = pstats.Stats("rand_trail_" + str(73) + "_hard_fixes.txt")
# p.sort_stats('tottime').print_stats(10)

# print("Tuesday 2")
# p = pstats.Stats("rand_trail_" + str(73) + "_hard_fixes_possible_hell_ed.txt")
# p.sort_stats('tottime').print_stats(10)

# print("rand_trail_73_hard_fixes_hell_ed_drop_pieces.txt")
# p = pstats.Stats("rand_trail_" + str(73) + "_hard_fixes_hell_ed_drop_pieces.txt")
# p.sort_stats('tottime').print_stats(10)

# print("rand_trail_73_hard_fixes_hell_ed_drop_pieces_2.txt")
# p = pstats.Stats("rand_trail_" + str(73) + "_hard_fixes_hell_ed_drop_pieces_2.txt")
# p.sort_stats('tottime').print_stats(10)

# print("rand_trail_73_window_bit_check.txt")
# p = pstats.Stats("rand_trail_" + str(73) + "_window_bit_check.txt")
# p.sort_stats('tottime').print_stats(10)

# print("rand_trail_73_dont_clean_if_no_match.txt")
# p = pstats.Stats("rand_trail_" + str(73) + "_dont_clean_if_no_match.txt")
# p.sort_stats('tottime').print_stats(10)

# print("updated better seed 73")
# p = pstats.Stats("rand_trail_" + str(73) + "_updated_2.txt")
# p.sort_stats('cumtime').print_stats(5)

# print("updated better seed 73 take 2")
# p = pstats.Stats("rand_trail_" + str(73) + "_updated_2.1.txt")
# p.sort_stats('cumtime').print_stats(5)

# print("updated better seed 936")
# p = pstats.Stats("rand_trail_" + str(936) + "_updated_2.txt")
# p.sort_stats('cumtime').print_stats(5)

# print("updated better seed 383")
# p = pstats.Stats("rand_trail_" + str(383) + "_updated_2.txt")
# p.sort_stats('cumtime').print_stats(5)

# print("updated better seed 295")
# p = pstats.Stats("rand_trail_" + str(295) + "_updated_2.txt")
# p.sort_stats('cumtime').print_stats(5)

# print("updated better seed 204")
# p = pstats.Stats("rand_trail_" + str(204) + "_updated_2.txt")
# p.sort_stats('cumtime').print_stats(5)

# print("updated better seed 204 take 2")
# p = pstats.Stats("rand_trail_" + str(204) + "_updated_2.1.txt")
# p.sort_stats('cumtime').print_stats(5)

# print("updated better seed 493")
# p = pstats.Stats("rand_trail_" + str(493) + "_updated_2.txt")
# p.sort_stats('cumtime').print_stats(5)
