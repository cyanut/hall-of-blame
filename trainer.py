from __future__ import absolute_import, division, print_function, unicode_literals

try:
    from pydds import dds
except ImportError:
    import dds
import ctypes
import re
from xml.dom import minidom
import traceback


suit_table = {"S":0, "H":1, "D":2, "C":3, "NT":4, "N":4}
hand_table = {"N":0, "E":1, "S":2, "W":3}
vul_table  = {"o":0, "b": 1, "n": 2, "e":3}
side_table = {"NS":0, "EW":1}
rank_table = {"A":14, "K":13, "Q":12, "J":11, "T":10, 
              "9":9, "8":8, "7":7, "6":6, "5":5, "4":4, "3":3, "2":2}
reverse_rank_table = {v: k for k, v in rank_table.items()}

seat_table = ["N", "E", "S", "W"]
suit_list = ["C", "D", "H", "S", "NT"]
seat_alias = ["north", "east", "south", "west"]
vul_dic = {'o':"None", 'b':"Both", 'n':"NS", 'e':"EW"}

def fmt_play_trace(pbn_play):
    c_pbn_play = re.sub("[- \n]","",pbn_play)
    c_pbn_play = re.sub("=[0-9]*=", "", c_pbn_play)
    n = len(c_pbn_play) // 2
    print(n)
    '''
    play_arr = []
    for suit,rank in zip(c_pbn_play[::2], c_pbn_play[1::2]):
        play_arr.append(suit_table[suit])
        play_arr.append(rank_table[rank])
    play_arr += [0, 0]
    c_pbn_play = "".join([chr(x) for x in play_arr])
    '''
    c_pbn_play = c_pbn_play.encode("utf-8")

    play = dds.playTracePBN(n, c_pbn_play)
    return play

def fmt_deal(pbn_deal, trump, lead_player, current_tricks=[]):
    pbn_deal = pbn_deal.strip().encode("utf-8")
    trump = suit_table[trump]
    lead_player = hand_table[lead_player]
    suit_array = (ctypes.c_int * 3)(*([0] * 3))
    trick_array = (ctypes.c_int * 3)(*([0] * 3))
    for i, card in enumerate(current_tricks):
        if i >= 3:
            return;
        else:
            suit_array[i] = suit_table[card[0]]
            trick_array[i] = rank_table[card[1]]

    deal = dds.dealPBN(trump, lead_player, suit_array, trick_array, pbn_deal)
    return deal

def format_future_tricks(future_tricks):
    card = []
    for i in range(future_tricks.cards):
        suit = suit_list[3-future_tricks.suit[i]]
        score = future_tricks.score[i]
        rank = [future_tricks.rank[i]]
        equal = future_tricks.equals[i] >> 2
        i = 2
        while equal > 0:
            if equal % 2 == 1:
                rank.append(i)
            i += 1
            equal >>= 1
        for r in rank:
            card.append([suit + reverse_rank_table[r],  score])
    return card


def get_correct_play(deal, trump, play_seq, seat_seq, error_seq):
    #deal = dictionary in the format of, e.g., {"N":{"H": "AKT93",...}
    working_deal = {seat: {suit: list(cards) for suit, cards in v} for seat,v in deal.items()} #deep copy, convert deal string to list
    p = 0
    deal_pbn_list = []
    bad_cards = []
    bad_card_owners = []
    for pos in range(len(error_seq)):
        if error_seq[pos] != 0:
            leader = seat_table[seat_seq[pos // 4 * 4]]
            current_tricks = play_seq[pos // 4 * 4: pos] #the rest are on the table now
            for p1 in range(p, pos):
                card = play_seq[p1]
                for hand, deal in working_deal.items():
                    try:
                        deal[card[0]].remove(card[1])
                    except ValueError:
                        continue
                    break
            p = pos
            hand_pbn = []
            for seat in seat_table:
                suit = ".".join(["".join(working_deal[seat][s]) for s in suit_list[3::-1]])
                hand_pbn.append(suit)
            pbn = "".join(["N:", " ".join(hand_pbn)])
            print(pbn, play_seq[pos], seat_seq[pos])
            deal_pbn_list.append(fmt_deal(pbn, trump, leader, current_tricks))
            bad_cards.append(play_seq[pos])
            bad_card_owners.append(seat_seq[pos])

    n_boards = dds.MAXNOOFBOARDS
    deal_pbn = (dds.dealPBN * n_boards)(*deal_pbn_list)
    target = (ctypes.c_int*n_boards)(*([-1] * n_boards))
    solutions = (ctypes.c_int*n_boards)(*([3] * n_boards))
    mode = (ctypes.c_int*n_boards)(*([0] * n_boards))
    n_boards = len(deal_pbn_list)
    boards_pbn = dds.boardsPBN(n_boards, deal_pbn, target, solutions, mode)

    board_result = dds.solvedBoards()
    res_p = ctypes.pointer(board_result)
    ret = dds.SolveAllBoards(boards_pbn, res_p)
    print("""!!!!!!!!!!!!!!!!!!!!!!!!!!!""", ret)
    board_result = map(format_future_tricks, list(board_result.solvedBoards)[:board_result.noOfBoards])
    board_result = dict(zip(bad_cards, list(zip(board_result, bad_card_owners))))
    return board_result
                


def analyze_par(pbn_deal, dealer, vul):
    table_deal_pbn = dds.ddTableDealPBN(pbn_deal.strip().encode("utf-8"))
    table_res = dds.ddTableResults()
    table_res_p = ctypes.pointer(table_res)
    ret = dds.CalcDDtablePBN(table_deal_pbn, table_res_p)
    if ret != 1:
        print("!!!!!", ret)
        return None
    dd_table_flat = []
    for y in table_res.resTable:
        dd_table_flat += list(y)
    dd_table = []
    for i in range(12, -1, -4):
        dd_table.append(dd_table_flat[i:i+4])
    dd_table.append(dd_table_flat[16:20])
    
    

    par_res = dds.parResultsDealer()
    par_res_p = ctypes.pointer(par_res)
    dealer = hand_table[dealer]
    vul = vul_table[vul]
    ret = dds.DealerPar(table_res_p, par_res_p, dealer, vul)
    if ret != 1:
        print("!!!!!!!", ret)
        return None
    return {"dd_table" : list(zip(suit_list, dd_table)),
            "score":par_res.score, 
            "contracts":[x.value.decode("utf-8").replace("*","x") for x in par_res.contracts[:par_res.number]]}

def analyze_play(pbn_deal, pbn_play, trump, lead_player, thread_id = 0):
    c_pbn_deal = fmt_deal(pbn_deal, trump, lead_player)
    c_pbn_play = fmt_play_trace(pbn_play)
    res = dds.solvedPlay()
    res_pointer = ctypes.pointer(res)
    print(len(pbn_play))
    ret = dds.AnalysePlayPBN(c_pbn_deal, c_pbn_play, res_pointer, thread_id)
    if ret == 1:
        tricks = list(res.tricks)[:res.number]  
        return tricks + (len(pbn_play) % 2 - res.number) * [tricks[-1]]
    else:
        print(ret)
        return None


def check_unique(l):
    if len(l) == 1:
        return l[0]
    else:
        return None


def node_to_dict(node):
    res = {}
    for k, attr in dict(node.attributes).items():
        res[k] = attr.value
    return res

def find_owner(deal, card):
    if card:
        suit_num = suit_table[card[0]]
        for seat, hand in deal.items():
            if card[1] in hand[suit_num][1]:
                return seat
    print(deal, card)
    return None
    

def format_board_res(packet_xml):
    board_node = packet_xml.getElementsByTagName("sc_board_details")
    board_node = check_unique(board_node)
    game_result = {}

    game_result["type"] = "this_table"

    game_result["board"] = node_to_dict(board_node)

    deal_node = packet_xml.getElementsByTagName("sc_deal")
    deal_node = check_unique(deal_node)
    game_result["deal"] = node_to_dict(deal_node)
    pbn = []
    game_result["deal"]["vul_parsed"] = vul_dic[game_result["deal"]["vul"]]
    dealer = game_result["deal"]["dealer"][0].upper()
    game_result["deal"]["dealer"] = dealer
    game_result["deal"]["dealer_num"] = hand_table[dealer]
    game_result["deal"]["all"] = {}
    for seating in seat_alias:
        hand = game_result["deal"][seating]
        hand_list = re.split("[SHDC]", hand)
        if len(hand_list) == 5:
            hand_list = hand_list[1:]
        hand_list=[x[::-1] for x in hand_list]
        game_result["deal"]["all"][seating[0].upper()] = list(zip(["S","H", "D", "C"], hand_list))
        hand = ".".join(hand_list)
        pbn.append(hand)
    #sort deals so it starts from dealer
    pbn += pbn
    pbn = pbn[hand_table[dealer]:hand_table[dealer]+4]
    pbn = " ".join(pbn)
    game_result["deal"]["pbn"] = "{}:{}".format(dealer, pbn)

    game_result["bids"] = []
    bid_nodes = packet_xml.getElementsByTagName("sc_call_made")
    for bid in bid_nodes:
        game_result["bids"].append(node_to_dict(bid))

    play = []
    play_nodes = packet_xml.getElementsByTagName("sc_card_played")
    for card in play_nodes:
        play.append(card.attributes["card"].value)
    game_result["play"] = {}
    game_result["play"]["cards"] = " ".join(play)

    #figure out trump and who made the lead
    '''
    res_string = game_result["board"]["result"]
    res = re.findall("([1-7]+)([HSDC]|NT)([NESW])([+-=][0-9]*)", res_string)
    res = check_unique(res)
    '''

    bids = game_result["bids"]
    declarer = None
    contract = None
    side = None
    double = 0
    # find out contract
    for i, bid in enumerate(bids[::-1]):
        if bid["call"] in ['d', 'r'] and not contract:
            double += 1
        if bid["call"] not in ['p', 'd', 'r'] and not contract:
            contract = bid["call"]
            side = i % 2
        if contract and i % 2 == side and len(bid["call"]) == len(contract) and bid["call"][1:] == contract[1:]:
            declarer = (len(bids) - i - 1) % 4 
    if declarer is not None and contract is not None:
        declarer = (declarer + hand_table[game_result["deal"]["dealer"]]) % 4
        game_result["deal"]["contract"] = contract
        game_result["deal"]["trump"] = contract[1:]
        game_result["deal"]["declarer"] = seat_table[declarer]
        #lead player is LHO declarer
        game_result["deal"]["lead_player"] = seat_table[(declarer + 1) % 4]
        game_result["analysis"] = {}
        print(game_result)
        game_result["analysis"]["play_tricks"] = analyze_play(\
            game_result["deal"]["pbn"],
            game_result["play"]["cards"].replace(" ", ""),
            game_result["deal"]["trump"],
            game_result["deal"]["lead_player"])

        #format play sequence
        play_tricks = game_result["analysis"]["play_tricks"]
        play_diff = [x[1]-x[0] for x in zip(play_tricks[:-1], play_tricks[1:])]
        play_cards = game_result["play"]["cards"].split(" ")

        if play_cards and play_cards[0]:
            print("play cards", play_cards)

            play_owner = [hand_table[find_owner(game_result["deal"]["all"], x)] for x in play_cards]
            play_seq = []
            print(len(play_cards), len(play_owner), len(play_diff), len(play_tricks))
            #input()
            for i in range(0, len(play_cards), 4):
                play_seq.append(sorted(list(zip(play_cards[i:i+4], 
                                         play_owner[i:i+4],
                                         play_diff[i:i+4],
                                         [True, False, False, False])), key=lambda x:x[1]))#is lead?
            game_result["analysis"]["play_anotated"] = play_seq
            correct_play = get_correct_play(game_result['deal']['all'],
                                            game_result["deal"]['trump'],
                                            play_cards,
                                            play_owner,
                                            play_diff)
            #convert side trick number to declarer trick number
            for k, v in correct_play.items():
                is_defence = v[1] % 2 ^ declarer % 2
                if is_defence == 0:
                    is_defence = -1
                # is_defence is 1 or -1

                max_trick = max([x[1] for x in v[0]])
                for card in v[0]:
                    card[1] = "{:+d}".format((max_trick - card[1]) * is_defence)

            game_result["deal"]["correct_play"] = correct_play
                                            
        else:
            game_result["deal"]["correct_play"] = []
        
        #parse result
        result = [game_result["deal"]["contract"]]
        result.append(game_result["deal"]["declarer"])
        for i in range(double):
            result.append("x")
        tricks = play_tricks[-1]
        target_tricks = int(game_result["deal"]["contract"][0]) + 6
        over_trick = tricks - target_tricks
        if over_trick == 0:
            result.append("=")
        else:
            result.append("{:+d}".format(over_trick))
        game_result["deal"]["result"] = "".join(result)


    
    else: # passed out
        game_result["deal"]["trump"] = 'P'
        game_result["deal"]["result"] = "Pass"

    game_result['board_num'] = int(game_result['deal']['board'])

    if not "analysis" in game_result:
        game_result["analysis"] = {}
    game_result["analysis"]["par"] = analyze_par(\
            game_result["deal"]["pbn"],
            game_result["deal"]["dealer"],
            game_result["deal"]["vul"])
    
    return game_result

def format_table_res(packet_xml):
    result_nodes = packet_xml.getElementsByTagName("sc_result")
    result_nodes = [node_to_dict(x) for x in result_nodes]
    result_nodes.sort(key=lambda x: float(x["rawscorens"]))
    
    board_num = packet_xml.getElementsByTagName("sc_board")
    board_num = check_unique(board_num)
    board_num = int(board_num.attributes["number"].value)
    return {"type":"other_tables", "board_num": board_num, "result":result_nodes}

def process_game_packet(packet, q):
    import pprint
    #print(packet)
    packet = packet.strip(b"\x00")

    try:
        packet_xml = minidom.parseString(packet)
    except Exception as e:
        print(traceback.format_exc())
        print(packet)
        #input()
        return
        

    board_node = packet_xml.getElementsByTagName("sc_board_details")
    board_node = check_unique(board_node)

    if board_node:
        result = format_board_res(packet_xml)

    else:
        other_table_node = packet_xml.getElementsByTagName("sc_boards")
        other_table_node = check_unique(other_table_node)
        if other_table_node:
            result = format_table_res(packet_xml)

    q.put(result)
    pprint.pprint(result)
    return


if __name__ == "__main__":
    pbn_deal = 'N:.Q853.AJ962.KT74 Q853.AJ962.KT74. AJ962.KT74..Q853 KT74..Q853.AJ962'
    pbn_play = 'SA ST HQ S3'
    res = analyze_play(pbn_deal, pbn_play, "S", "S").tricks
    print(list(res))


