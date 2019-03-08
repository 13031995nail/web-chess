from django.shortcuts import render
from django.http import HttpResponse
import chess
import re
import copy
import tensorflow as tf
import numpy as np
import chess.pgn
import itertools
import math
import json

def index(request):
    return render(request, "index.html", {'board': 'rnbqkbnrpppppppp11111111111111111111111111111111PPPPPPPPRNBQKBNR'})

def new_game(request):
    data = {
        "moves": [],
        "moveTotal": 0
    }
    with open("hello/moves.json", "w") as write_file:
        json.dump(data, write_file)
    return render(request, "index.html", {'board': 'rnbqkbnrpppppppp11111111111111111111111111111111PPPPPPPPRNBQKBNR'})

def move(request, move):
    board = chess.Board()

    with open("hello/moves.json", "r") as read_file:
        data = json.load(read_file)

    moves = data["moves"]
    moveTotal = data["moveTotal"]

    for i in moves:
        move_star = chess.Move.from_uci(i)
        board.push(move_star)

    depth = 1

    if moveTotal % 2 == 1:
        move_new = chess.Move.from_uci(move)
        board.push(move_new)
        mystr = board.fen()
        mystr = mystr[:mystr.find(" ")]
        mystr = re.sub(r"[/]", "", mystr)
        for i in range(2,9,1):
            stroke = ""
            for j in range(i):
                stroke += str(1)
            mystr = re.sub(str(i), stroke, mystr)
        moves.append(move)
    else:
        board_net = computerMove(board, depth)
        move_net = str(board_net.peek())
        mystr = board_net.fen()
        mystr = mystr[:mystr.find(" ")]
        mystr = re.sub(r"[/]", "", mystr)
        for i in range(2, 9, 1):
            stroke = ""
            for j in range(i):
                stroke += str(1)
            mystr = re.sub(str(i), stroke, mystr)
        moves.append(move_net)
    moveTotal = moveTotal + 1
    data = {
        "moves": moves,
        "moveTotal": moveTotal
    }
    with open("hello/moves.json", "w") as write_file:
        json.dump(data, write_file)
    return render(request, "index.html", {'board': mystr, 'move': moves, 'moveTotal': moveTotal})

def netPredict(first, second):
    x_1 = bitifyFEN(beautifyFEN(first.fen()))
    x_2 = bitifyFEN(beautifyFEN(second.fen()))

    global x, y, init, saver

    toEval = [[x_1,x_2]]
    with tf.Session() as sess:
        sess.run(init_op)
        saver.restore(sess, 'hello/net/model_epoch-53')
        result = sess.run(y, feed_dict={x: toEval})

    if result[0][0] > result [0][1]:
        return (first, second)
    else:
        return (second, first)

def fully_connected(current_layer, weight, bias):
    next_layer = tf.add(tf.matmul(current_layer, weight), bias)
    next_layer = tf.maximum(0.01*next_layer, next_layer)
    return next_layer

def encode(c, weights, biases, level):
    e1 = fully_connected(c, weights['e1'], biases['e1'])
    if level == 1:
        return e1

    e2 = fully_connected(e1, weights['e2'], biases['e2'])
    if level == 2:
        return e2

    e3 = fully_connected(e2, weights['e3'], biases['e3'])
    if level == 3:
        return e3

    e4 = fully_connected(e3, weights['e4'], biases['e4'])
    return e4

def model(games, weights, biases):
    first_board = games[:,0,:]
    second_board = games[:,1,:]

    # [None, 769] -> [None, 600] -> [None, 400] -> [None, 200] -> [None, 100]
    firstboard_encoding = encode(first_board, weights, biases, 4)
    secondboard_encoding = encode(second_board, weights, biases, 4)

    # [None, 200] -> [None, 400] -> [None, 200] -> [None, 100] -> [None, 2]
    h_1 = tf.concat([firstboard_encoding,secondboard_encoding], 1)
    h_2 = fully_connected(h_1, weights['w1'], biases['b1'])
    h_3 = fully_connected(h_2, weights['w2'], biases['b2'])
    h_4 = fully_connected(h_3, weights['w3'], biases['b3'])

    pred = tf.add(tf.matmul(h_4, weights['w4']), biases['out'], name="output")
    return pred

def weight_variable(n_in, n_out):
    cur_dev = math.sqrt(3.0/(n_in+n_out))
    initial = tf.truncated_normal([n_in, n_out], stddev=cur_dev)
    return tf.Variable(initial)

def bias_variable(n_out):
    initial = tf.constant(0.15, shape=[n_out])
    return tf.Variable(initial)

def alphabeta(node, depth, alpha, beta, maximizingPlayer):
    if depth == 0:
        return node
    if maximizingPlayer:
        v = -1
        for move in node.legal_moves:
            cur = copy.copy(node)
            cur.push(move)
            if v == -1:
                v = alphabeta(cur, depth-1, alpha, beta, False)
            if alpha == -1:
                alpha = v

            v = netPredict(v, alphabeta(cur, depth-1, alpha, beta, False))[0]
            alpha = netPredict(alpha, v)[0]
            if beta != 1:
                if netPredict(alpha, beta)[0] == alpha:
                    break
        return v
    else:
        # если глубина больше 1
        v = 1
        for move in node.legal_moves:
            cur = copy.copy(node)
            cur.push(move)
            if v == 1:
                v = alphabeta(cur, depth-1, alpha, beta, True)
            if beta == 1:
                beta = v

            v = netPredict(v, alphabeta(cur, depth-1, alpha, beta, True))[1]
            beta = netPredict(beta, v)[1]
            if alpha != -1:
                if netPredict(alpha, beta)[0] == alpha:
                    break
        return v

def computerMove(board, depth):
    alpha = -1
    beta = 1
    v = -1
    # board.legal_moves - все возможные ходы из данного расположения фигур на доске (сеть играет белыми)
    for move in board.legal_moves:
        cur = copy.copy(board)
        cur.push(move)
        if v == -1:
            v = alphabeta(cur, depth-1, alpha, beta, False)
            bestMove = move
            if alpha == -1:
                alpha = v
        else:
            new_v = netPredict(alphabeta(cur, depth-1, alpha, beta, False), v)[0]
            if new_v != v:
                bestMove = move
                v = new_v
            alpha = netPredict(alpha, v)[0]

    board.push(bestMove)
    return board


pieces = {
    'p': 1,
    'P': -1,
    'n': 2,
    'N': -2,
    'b': 3,
    'B': -3,
    'r': 4,
    'R': -4,
    'q': 5,
    'Q': -5,
    'k': 6,
    'K': -6
}


def shortenString(s):
    s = s[:s.rfind(" ")]
    return s

def beautifyFEN(f):
    for i in range(4):
        f = shortenString(f)
    # После цикла: f = 'rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b'
    toMove = f[-1]
    if toMove == 'w':  # если предстоит ход белых
        toMove = 7
    else:
        toMove = -7

    f = shortenString(f)
    # f = 'rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR'
    newf = []

    for char in f:
        if char.isdigit():  # если символ цифра
            for i in range(int(char)):
                newf.append(0)
        elif char != '/':
            newf.append(pieces[char])
    newf.append(toMove)
    return newf

def bitifyFEN(f):  # f - одномерный массив целых чисел от -7 до 7 размера 65
    arrs = []
    result = []
    s = {
        '1': 0,
        '2': 1,
        '3': 2,
        '4': 3,
        '5': 4,
        '6': 5,
        '-1': 6,
        '-2': 7,
        '-3': 8,
        '-4': 9,
        '-5': 10,
        '-6': 11,
    }
    # arrs - массив формы 12x64 (12 определяет количество фигур)
    for i in range(12):
        arrs.append(np.zeros(64))

    for i in range(64):
        c = str(int(f[i]))
        if c != '0':  # если в i-ой позиции доски есть фигура
            c = s[c]
            # c = s[int(round(c))]
            arrs[c][i] = 1

    for i in range(12):
        result.append(arrs[i])

    # возвращает генератор, на каждой итерации возвращает элементы сначала из первого элемента и т. д.
    result = list(itertools.chain.from_iterable(result))

    if f[64] == -7:
        result.append(1)
    else:
        result.append(0)

    return result  # одномерный массив из 0 и 1 размера 769

ENCODING_1 = 600
ENCODING_2 = 400
ENCODING_3 = 200
ENCODING_4 = 100

HIDDEN_1 = 200
HIDDEN_2 = 400
HIDDEN_3 = 200
HIDDEN_4 = 100

N_INPUT =769
N_OUT = 2

weights = {
    'e1': weight_variable(N_INPUT, ENCODING_1),
    'e2': weight_variable(ENCODING_1, ENCODING_2),
    'e3': weight_variable(ENCODING_2, ENCODING_3),
    'e4': weight_variable(ENCODING_3, ENCODING_4),
    'd1': weight_variable(ENCODING_4, ENCODING_3),
    'd2': weight_variable(ENCODING_3, ENCODING_2),
    'd3': weight_variable(ENCODING_2, ENCODING_1),
    'd4': weight_variable(ENCODING_1, N_INPUT),
    'w1': weight_variable(HIDDEN_1, HIDDEN_2),
    'w2': weight_variable(HIDDEN_2, HIDDEN_3),
    'w3': weight_variable(HIDDEN_3, HIDDEN_4),
    'w4': weight_variable(HIDDEN_4, N_OUT)
}

biases = {
    'e1': bias_variable(ENCODING_1),
    'e2': bias_variable(ENCODING_2),
    'e3': bias_variable(ENCODING_3),
    'e4': bias_variable(ENCODING_4),
    'd1': bias_variable(ENCODING_3),
    'd2': bias_variable(ENCODING_2),
    'd3': bias_variable(ENCODING_1),
    'd4': bias_variable(N_INPUT),
    'b1': bias_variable(HIDDEN_2),
    'b2': bias_variable(HIDDEN_3),
    'b3': bias_variable(HIDDEN_4),
    'out': bias_variable(N_OUT)
}

x = tf.placeholder(tf.float32, shape=[None, 2, N_INPUT], name="input")
y = model(x, weights, biases)
init_op = tf.global_variables_initializer()
saver = tf.train.Saver()
