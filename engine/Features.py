#!/usr/bin/python
import os
import os.path
import random
from SGFParser import *

def make_color_plane(array, board, color):
    np.copyto(array, np.equal(board.vertices, color))

def make_ones_plane(array, board):
    np.copyto(array, np.ones((board.N, board.N), dtype=np.int8))

def make_history_planes(array, board, max_lookback):
    assert array.shape[2] == max_lookback
    for lookback in xrange(max_lookback):
        if lookback < len(board.move_list):
            move = board.move_list[-1-lookback]
            if move: # if not pass
                x,y = move
                array[x,y,lookback] = 1

def slow_count_group_liberties(board, start_x, start_y, visited):
    group_xys = [(start_x, start_y)]
    visited[start_x, start_y] = True
    group_color = board[start_x, start_y]
    liberties = set()
    i = 0
    while i < len(group_xys):
        x,y = group_xys[i]
        i += 1
        for dx,dy in dxdys:
            adj_x, adj_y = x+dx, y+dy
            if board.is_on_board(adj_x, adj_y):
                adj_color = board[adj_x, adj_y]
                if adj_color == Color.Empty:
                    liberties.add((adj_x, adj_y))
                elif adj_color == group_color and not visited[adj_x, adj_y]:
                    group_xys.append((adj_x, adj_y))
                    visited[adj_x, adj_y] = True
    return len(liberties), group_xys

def slow_make_liberty_count_planes(array, board, Nplanes, play_color):
    assert Nplanes % 2 == 0
    assert array.shape[2] == Nplanes
    visited = np.zeros((board.N, board.N), dtype=np.bool_) 
    for x in xrange(board.N):
        for y in xrange(board.N):
            if board[x,y] != Color.Empty and not visited[x,y]:
                num_liberties, group_xys = slow_count_group_liberties(board, x, y, visited)
                # First Nplanes/2 planes: 0=(play color, 1 liberty), 1=(player color, 2 liberties), ...
                # Next  Nplanes/2 planes: Np/2=(other color, 1 liberty), 1+Np/2=(other color, 2 liberties), ...
                if num_liberties > Nplanes/2: num_liberties = Nplanes/2
                plane = num_liberties - 1
                if board[x,y] != play_color:
                    plane += Nplanes/2
                for gx,gy in group_xys:
                    array[gx,gy,plane] = 1

def make_liberty_count_planes(array, board, Nplanes, play_color):
    assert Nplanes % 2 == 0
    assert array.shape[2] == Nplanes
    for group in board.all_groups:
        num_liberties = len(group.liberties)
        if num_liberties > Nplanes/2: num_liberties = Nplanes/2
        plane = num_liberties - 1
        if board[next(iter(group.vertices))] != play_color:
            plane += Nplanes/2
        for gx,gy in group.vertices:
            array[gx,gy,plane] = 1

    ### TEST
    #slow_liberty_count_planes = np.zeros((board.N, board.N, Nplanes))
    #slow_make_liberty_count_planes(slow_liberty_count_planes, board, Nplanes, play_color)
    #assert np.array_equal(slow_liberty_count_planes, array)

def make_capture_count_planes(array, board, Nplanes, play_color):
    capture_counts = {}
    for group in board.all_groups:
        assert len(group.vertices) > 0
        if group.color != play_color and len(group.liberties) == 1:
            capture_vertex = next(iter(group.liberties))
            if capture_vertex != board.simple_ko_vertex:
                if capture_vertex in capture_counts:
                    capture_counts[capture_vertex] += len(group.vertices)
                else:
                    capture_counts[capture_vertex] = len(group.vertices)
    for vert in capture_counts:
        x,y = vert
        count = capture_counts[vert]
        if count > Nplanes: count = Nplanes
        array[x,y,count-1] = 1

# too slow
def make_legality_plane(array, board, play_color):
    for x in xrange(board.N):
        for y in xrange(board.N):
            if board.play_is_legal(x, y, play_color):
                array[x,y] = 1

def make_simple_ko_plane(array, board):
    if board.simple_ko_vertex:
        array[board.simple_ko_vertex] = 1

# us, them, empty, ones
def make_feature_planes_stones(board, play_color):
    Nplanes = 4
    feature_planes = np.zeros((board.N, board.N, Nplanes), dtype=np.int8)
    make_color_plane(feature_planes[:,:,0], board, play_color)
    make_color_plane(feature_planes[:,:,1], board, flipped_color[play_color])
    make_color_plane(feature_planes[:,:,2], board, Color.Empty)
    make_ones_plane(feature_planes[:,:,3], board)
    return feature_planes

def make_feature_planes_stones_3liberties(board, play_color):
    Nplanes = 10
    feature_planes = np.zeros((board.N, board.N, Nplanes), dtype=np.int8)
    make_color_plane(feature_planes[:,:,0], board, play_color)
    make_color_plane(feature_planes[:,:,1], board, flipped_color[play_color])
    make_color_plane(feature_planes[:,:,2], board, Color.Empty)
    make_ones_plane(feature_planes[:,:,3], board)
    max_liberties = 3
    make_liberty_count_planes(feature_planes[:,:,4:10], board, 2*max_liberties, play_color)
    return feature_planes

def make_feature_planes_stones_4liberties(board, play_color):
    Nplanes = 12
    feature_planes = np.zeros((board.N, board.N, Nplanes), dtype=np.int8)
    make_color_plane(feature_planes[:,:,0], board, play_color)
    make_color_plane(feature_planes[:,:,1], board, flipped_color[play_color])
    make_color_plane(feature_planes[:,:,2], board, Color.Empty)
    make_ones_plane(feature_planes[:,:,3], board)
    max_liberties = 4
    make_liberty_count_planes(feature_planes[:,:,4:12], board, 2*max_liberties, play_color)
    return feature_planes

def make_feature_planes_stones_3liberties_4history_ko(board, play_color):
    Nplanes = 15
    feature_planes = np.zeros((board.N, board.N, Nplanes), dtype=np.int8)
    make_color_plane(feature_planes[:,:,0], board, play_color)
    make_color_plane(feature_planes[:,:,1], board, flipped_color[play_color])
    make_color_plane(feature_planes[:,:,2], board, Color.Empty)
    make_ones_plane(feature_planes[:,:,3], board)
    max_liberties = 3
    make_liberty_count_planes(feature_planes[:,:,4:10], board, 2*max_liberties, play_color)
    max_lookback = 4
    make_history_planes(feature_planes[:,:,10:14], board, max_lookback)
    make_simple_ko_plane(feature_planes[:,:,14], board)
    return feature_planes

def make_feature_planes_stones_3liberties_4history_ko_4captures(board, play_color):
    Nplanes = 19
    feature_planes = np.zeros((board.N, board.N, Nplanes), dtype=np.int8)
    make_color_plane(feature_planes[:,:,0], board, play_color)
    make_color_plane(feature_planes[:,:,1], board, flipped_color[play_color])
    make_color_plane(feature_planes[:,:,2], board, Color.Empty)
    make_ones_plane(feature_planes[:,:,3], board)
    max_liberties = 3
    make_liberty_count_planes(feature_planes[:,:,4:10], board, 2*max_liberties, play_color)
    max_lookback = 4
    make_history_planes(feature_planes[:,:,10:14], board, max_lookback)
    make_simple_ko_plane(feature_planes[:,:,14], board)
    max_captures = 4
    make_capture_count_planes(feature_planes[:,:,15:19], board, max_captures, play_color)
    return feature_planes

def apply_random_symmetries(many_feature_planes, many_move_arrs):
    N = many_feature_planes.shape[1]
    for i in range(many_feature_planes.shape[0]):
        if random.random() < 0.5: # flip x
            many_feature_planes[i,:,:,:] = many_feature_planes[i,::-1,:,:]
            many_move_arrs[i,0] = N - many_move_arrs[i,0] - 1
        if random.random() < 0.5: # flip y
            many_feature_planes[i,:,:,:] = many_feature_planes[i,:,::-1,:]
            many_move_arrs[i,1] = N - many_move_arrs[i,1] - 1
        if random.random() < 0.5: # swap x and y
            many_feature_planes[i,:,:,:] = np.transpose(many_feature_planes[i,:,:,:], (1,0,2))
            many_move_arrs[i,:] = many_move_arrs[i,::-1]
        assert 0 <= many_move_arrs[i,0] < N
        assert 0 <= many_move_arrs[i,1] < N
        assert many_feature_planes[i, many_move_arrs[i,0], many_move_arrs[i,1], 2] == 1 # basic check, assumes plane #2 is Color.Empty



class FeatureTester:
    def __init__(self, N):
        self.N = N
        self.player = PlayingProcessor(self.N)

    def begin_game(self):
        self.player.begin_game()
        self.ignore_game = False
    
    def end_game(self):
        print "Passed all tests for that game!"
        self.player.end_game()
        
    def test_color_plane(self, plane, color):
        for x in xrange(self.N):
            for y in xrange(self.N):
                assert (plane[x,y] == 1) or (plane[x,y] == 0)
                assert (plane[x,y] == 1) == (self.player.board[x,y] == color)

    def test_ones_plane(self, plane):
        for x in xrange(self.N):
            for y in xrange(self.N):
                assert plane[x,y] == 1

    def test_liberty_count_planes(self, planes, play_color):
        Nplanes = planes.shape[2]
        for x in xrange(self.N):
            for y in xrange(self.N):
                expected_column = np.zeros((Nplanes,), dtype=np.int8)
                if self.player.board[x,y] != Color.Empty:
                    liberty_count, _ = slow_count_group_liberties(self.player.board, x, y, np.zeros((self.N, self.N), dtype=np.bool_))
                    plane = liberty_count - 1
                    if plane >= Nplanes/2: plane = Nplanes/2 - 1
                    if self.player.board[x,y] != play_color: plane += Nplanes/2
                    expected_column[plane] = 1
                assert np.array_equal(planes[x,y,:], expected_column)

    def test_legality_planes(self, plane, play_color):
        for x in xrange(self.N):
            for y in xrange(self.N):
                assert (plane[x,y] == 1) or (plane[x,y] == 0)
                assert (plane[x,y] == 1) == self.player.board.play_is_legal(x, y, play_color)

    def test_simple_ko_plane(self, plane):
        for x in xrange(self.N):
            for y in xrange(self.N):
                assert (plane[x,y] == 1) or (plane[x,y] == 0)
                assert (plane[x,y] == 1) == ((x,y) == self.player.board.simple_ko_vertex)

    def test_history_planes(self, planes):
        max_lookback = planes.shape[2]
        for lookback in xrange(max_lookback):
            for x in xrange(self.N):
                for y in xrange(self.N):
                    assert (planes[x,y,lookback] == 0) or (planes[x,y,lookback] == 1)
                    if planes[x,y,lookback] == 1:
                        assert self.player.board.move_list[-1-lookback] == (x,y)
        for lookback in xrange(max_lookback):
            if lookback < len(self.player.board.move_list):
                move = self.player.board.move_list[-1-lookback]
                if move: # if not pass
                    x,y = move
                    assert planes[x,y,lookback] == 1


    def test_features(self, play_color):
        feature_planes = make_feature_planes_stones_3liberties_4history_ko_4captures(self.player.board, play_color)
        self.test_color_plane(feature_planes[:,:,0], play_color)
        self.test_color_plane(feature_planes[:,:,1], flipped_color[play_color])
        self.test_color_plane(feature_planes[:,:,2], Color.Empty)
        self.test_ones_plane(feature_planes[:,:,3])
        self.test_liberty_count_planes(feature_planes[:,:,4:10], play_color)
        self.test_history_planes(feature_planes[:,:,10:14])
        self.test_simple_ko_plane(feature_planes[:,:,14])
        # not yet testing captures
        # not yet testing legality

    def process(self, property_name, property_data):
        if property_name == "W":
            self.test_features(Color.White)
        elif property_name == "B":
            self.test_features(Color.Black)
        self.player.process(property_name, property_data)


def test_features_on_KGS():
    base_dir = "/home/greg/coding/ML/go/NN/data/KGS/SGFs"
    print "Making list of SGFs..."
    all_sgfs = []
    for period_dir in os.listdir(base_dir):
        for sgf_file in os.listdir(os.path.join(base_dir, period_dir)):
            filename = os.path.join(base_dir, period_dir, sgf_file)
            all_sgfs.append(filename)
    random.shuffle(all_sgfs)

    for sgf in all_sgfs:
        parse_SGF(sgf, FeatureTester(19))


if __name__ == "__main__":
    test_features_on_KGS()




