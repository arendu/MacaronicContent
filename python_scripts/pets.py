#!/usr/bin/env python
__author__ = 'arenduchintala'
from itertools import groupby, product
import sys
import pdb


class SplitNode(object):
    def __init__(self, sp1, sp2, o_idx1, o_idx2, g_idx1, g_idx2, swap, head=0):
        assert isinstance(sp1, list)
        assert isinstance(sp2, list)
        assert len(sp1) == len(o_idx1)
        assert len(sp2) == len(o_idx2)
        self.split1 = sp1
        self.split2 = sp2
        self.o_idx1 = o_idx1
        self.o_idx2 = o_idx2
        self.g_idx1 = g_idx1
        self.g_idx2 = g_idx2
        self.fullg = g_idx1 + g_idx2
        self.g1_in_order = in_order(self.g_idx1)
        self.g2_in_order = in_order(self.g_idx2)
        self.parent = None
        self.children1 = []
        self.children2 = []
        self.swap = swap
        self.head = head
        self.non_itg_split1 = False
        self.non_itg_split2 = False
        #print 'new split', str(self)


    def __str__(self):
        self_str = ""
        self_str += "swap:" + str(self.swap) 
        self_str += " head:" + str(self.head) 
        self_str += " g1:" + str(self.g_idx1) 
        self_str += " g1_in_order:" + str(self.g1_in_order) 
        self_str += " group2:" + str(self.g_idx2)
        self_str += " g2_in_order:" + str(self.g2_in_order) 
        self_str += " span:" + str(self.g_idx1 + self.g_idx2) 

        return self_str

    def keep_one(self):
        #print 'parent', str(self), 'num c1', len(self.children1),'g1 in order', self.g1_in_order,  'num c2', len(self.children2), 'g2 in order', self.g2_in_order
        if len(self.children1) > 1:
            for c in self.children1[1:]:
                print 'removing', str(c)
            self.children1 = self.children1[:1]
            print 'keeping', self.children1[0]
        if len(self.children2) > 1:
            for c in self.children2[1:]:
                print 'removing', str(c)
            self.children2 = self.children2[:1]
            print 'keeping', self.children2[0]
        for c in self.children1:
            c.keep_one()
        for c in self.children2:
            c.keep_one()
        return True

    def get_one_derivation(self, p, rules=[]):
        print 'one derivation', self.split1 
        rules.append((self.swap, self.g_idx1, self.g_idx2, p, self.head, self))
        for c in self.children1[:1]:
            c.get_one_derivation(self.split1, rules)
        for c in self.children2[:1]:
            c.get_one_derivation(self.split2, rules)
        return rules

    def add_child(self, sn, id):
        assert isinstance(sn, SplitNode)
        assert isinstance(id, int)
        sn.parent = self
        assert isinstance(sn, SplitNode)
        if id == 1:
            self.children1.append(sn)
        else:
            self.children2.append(sn)


def splits_to_str(sp1, sp2, s_idx1, s_idx2):
    str_sp1 = ','.join([str(i) for i in sp1])
    str_sp2 = ','.join([str(i) for i in sp2])
    str_s_idx1 = ','.join([str(i) for i in s_idx1])
    str_s_idx2 = ','.join([str(i) for i in s_idx2])
    return '|'.join([str_sp1, str_sp2, str_s_idx1, str_s_idx2])


def str_to_splits(str_splits):
    [str_sp1, str_sp2, str_s_idx1, str_s_idx2] = str_splits.split('|')
    sp1 = [int(i) for i in str_sp1.split(',')]
    sp2 = [int(i) for i in str_sp2.split(',')]
    s_idx1 = [int(i) for i in str_s_idx1.split(',')]
    s_idx2 = [int(i) for i in str_s_idx2.split(',')]
    return sp1, sp2, s_idx1, s_idx2


def overlaps(p1, p2):
    mp1 = min(p1[0], p1[1])
    mp2 = min(p2[0], p2[1])
    if mp1 > mp2:
        if mp1 > p2[1] and mp1 > p2[0]:
            return True
    if mp2 > mp1:
        if mp2 > p1[0] and mp2 > p1[1]:
            return True
    return False


def check_consistency2(split1, split2):
    r1 = (min(split1), max(split1))
    r2 = (min(split2), max(split2))
    if not overlaps(r1, r2):
        return False
    else:
        return True

def potential_split_points(alignment):
    split_points = []
    for idx, a in enumerate(alignment):
        if idx > 0:
            prev_a = alignment[idx - 1]
        else:
            prev_a = a

        if idx < len(alignment) - 1:
            next_a = alignment[idx + 1]
        else:
            next_a = a

        sp = abs(next_a - a) > 1 or abs(prev_a - a) > 1
        split_points.append(not sp)
    return split_points


def get_splits(alignment, idx_a, idx_g):
    assert alignment == idx_g
    #print alignment, idx_a, idx_g, 'try to find splits'
    #min_a = min(alignment)
    #a_monotonic = [abs(idx - a) == min_a for idx, a in enumerate(alignment)]
    #a_mon = potential_split_points(alignment)
    #a_monotonic = a_mon
    splits = []
    alignment_in_order = in_order(alignment)
    if alignment_in_order:
        #print 'already in order', alignment
        return splits
    #print 'trying to split', alignment
    for m in range(1, len(alignment)):
        split1_a = alignment[:m]
        split1_idx = idx_a[:m]
        split1_g = idx_g[:m]
        split2_a = alignment[m:]
        split2_idx = idx_a[m:]
        split2_g = idx_g[m:]
        if check_consistency2(split1_a, split2_a):
            #print 'splitting', split1_a, split2_a,m
            min_1 = min(split1_a)
            min_2 = min(split2_a)
            swaps = min_1 > min_2
            splits.append((split1_a, split2_a, split1_idx, split2_idx, split1_g, split2_g, swaps))
        else:
            #print 'skipping', split1_a, split2_a,m
            pass
    #print 'found', len(splits), 'splits for span', alignment
    return splits


def check_for_heads(dep_parse, coe_sentence, gidx1, gidx2, vis_lang):
    if coe_sentence is None:
        return True, 0
    g_phrase1 = [coe_sentence.get_graph_by_id(gid).get_visible_phrase_with_idx(vis_lang)
                 for gid in gidx1]
    g_phrase2 = [coe_sentence.get_graph_by_id(gid).get_visible_phrase_with_idx(vis_lang)
                 for gid in gidx2]
    g1_phrase = [val for sublist in g_phrase1 for val in sublist]
    g2_phrase = [val for sublist in g_phrase2 for val in sublist]

    # dependency edge from group 1 to group 2
    g1_g2 = False
    for g1, g2 in product(g1_phrase, g2_phrase):
        if (g1, g2) in dep_parse:
            g1_g2 = True

    # dependency edge from group 2 to group 1
    g2_g1 = False
    for g1, g2 in product(g2_phrase, g1_phrase):
        if (g1, g2) in dep_parse:
            g2_g1 = True
    '''
    g1_g1 = False
    for g1a, g1b in product(g1_phrase, g1_phrase):
        if (g1a, g1b) in dep_parse:
            g1_g1 = True

    g2_g2 = False
    for g2a, g2b in product(g2_phrase, g2_phrase):
        if (g2a, g2b) in dep_parse:
            g2_g2 = True
    '''

    if g1_g2 and not g2_g1:
        # print 'valid split and group 1 is the head', g1_g2, g1_g1, g2_g1, g2_g2
        return True, 1
    elif g2_g1 and not g1_g2:
        # print 'valid split and group 2 is the head', g1_g2, g1_g1, g2_g1, g2_g2
        return True, 2
    elif not g1_g2 and not g2_g1:
        # print 'valid split no head/dependent relations', g1_g2, g1_g1, g2_g1, g2_g2
        return True, 0  # valid split no head/dependent interaction
    else:
        # print 'not a valid split', g1_g2, g1_g1, g2_g1, g2_g2
        return False, 0  # not a valid split

def in_order(lst):
    order = True
    for i in range(1, len(lst)):
        if lst[i] >= lst[i-1]:
            pass
        else:
            return False
    return True

def get_unique(tok_group):
    u = set([])
    tok_idx = []
    tok_unique = []
    for t_idx, t in enumerate(tok_group):
        if t not in u:
            u.add(t)
            tok_unique.append(t)
            tok_idx.append(t_idx)
    return tok_unique, tok_idx


def get_split_sets(split_inp, split_out):
    split_sets = []
    for i, j in split_inp.items():
        s = set([i] + j[0])
        split_sets.append(s)
    for i, j in split_out.items():
        s = set([i] + j[0])
        split_sets.append(s)
    return split_sets


def get_swap_rules(coe_sentence, input_tok_group, output_tok_group, dep_parse, split_sets, vis_lang):
    non_itg_spans = []
    swap_rules = []
    #input_unique = [i[0] for i in groupby(input_tok_group)]
    #output_unique = [i[0] for i in groupby(output_tok_group)]
    input_unique, input_idx = get_unique(input_tok_group)
    output_unique, output_idx = get_unique(output_tok_group)
    alignment = [output_unique.index(i) for i in input_unique]
    alignment_idx = range(len(alignment))
    #min_a = min(alignment)
    #a_monotonic = [abs(idx - a) == min_a for idx, a in enumerate(alignment)]
    #a_monotonic_new = a_monotonic
    #a_monotonic_new = [a_monotonic[idx + 1 - 1: idx + 1 + 2].count(0) == 0 for idx, am in enumerate(a_monotonic[1:])]
    #print a_monotonic_new
    #a_monotonic_new = [False] * len(a_monotonic_new)
    #print a_monotonic_new
    align_direction = [True]
    align_direction_rev  = [True]
    for a_idx, a in enumerate(alignment[1:]):
        if a - alignment[a_idx] == 1 and align_direction[-1]:
            align_direction.append(True)
        else:
            align_direction.append(False)
    for a_idx, a in reversed(list(enumerate(alignment[:-1]))):
        if a - alignment[a_idx + 1] == -1 and align_direction_rev[-1]:
            align_direction_rev.append(True)
        else:
            align_direction_rev.append(False)
    align_direction_rev.pop(0)
    align_direction_rev.reverse()
    align_direction.pop(0)
    assert len(align_direction) == len(align_direction_rev)
    a_monotonic_2 = []
    for f,r in zip(align_direction, align_direction_rev):
        a_monotonic_2.append(f or r)
    a_monotonic_final = [None] * len(a_monotonic_2)
    for a_idx, a in enumerate(a_monotonic_2):
        if a_idx == 0:
            a_monotonic_final[a_idx] = a_monotonic_2[a_idx]
        elif a_idx > 0 and a_idx < len(a_monotonic_2) - 1:
            a_monotonic_final[a_idx] = a_monotonic_2[a_idx-1] and a and a_monotonic_2[a_idx + 1]
        else:
            a_monotonic_final[a_idx] = a_monotonic_2[a_idx]

    #print align_direction, len(align_direction), len(a_monotonic_new)
    #print align_direction_rev, len(align_direction_rev), len(a_monotonic_new)
    #print a_monotonic_2, '<-', len(a_monotonic_2)
    #print a_monotonic_final, '<-', len(a_monotonic_final)

    a_monotonic_new = a_monotonic_final
    list_of_lists = []
    prev_split = 0
    for idx, am in enumerate(a_monotonic_new):
        if idx > 0:
            if am != a_monotonic_new[idx - 1]:
                sub_list = a_monotonic_new[prev_split:idx]
                sub_alignment = alignment[prev_split:idx]
                sub_alignment_idx = alignment_idx[prev_split:idx]
                sub_g_idx = input_unique[prev_split:idx]
                prev_split = idx
                if False in sub_list:
                    list_of_lists.append((sub_alignment, sub_alignment_idx, sub_g_idx))
        if idx == len(a_monotonic_new) - 1:
            sub_list = a_monotonic_new[prev_split:]
            sub_alignment = alignment[prev_split:]
            sub_alignment_idx = alignment_idx[prev_split:]
            sub_g_idx = input_unique[prev_split:]
            if False in sub_list:
                list_of_lists.append((sub_alignment, sub_alignment_idx, sub_g_idx))
    for align, align_idx, sub_g_idx in list_of_lists:
        rs = []
        root_node = SplitNode([], align, [], align_idx, [], sub_g_idx, False, 2)
        _stack = [root_node]
        while len(_stack) > 0:
            sn = _stack.pop()
            if len(sn.split1) > 1:
                splits = get_splits(sn.split1, sn.o_idx1, sn.g_idx1)
                if len(splits) == 0 and not in_order(sn.split1):
                    #print sn.split1, 'is not ITG compliant'
                    sn.non_itg_split1 = True
                else:
                    #print 'no reordering in', sn.split1
                    pass
                for s1, s2, s_idx1, s_idx2, gidx1, gidx2, swaps in splits:
                    legal = True
                    head = 0
                    if swaps:
                        #print  gidx1, 'swaps with',  gidx2
                        legal, head = check_for_heads(dep_parse, coe_sentence, gidx1, gidx2, vis_lang)
                    if legal:
                        sn_child = SplitNode(s1, s2, s_idx1, s_idx2, gidx1, gidx2, swaps, head)
                        sn.add_child(sn_child, 1)
                        _stack.append(sn_child)
                    else:
                        print 'blocking illeagal swap', gidx1, gidx2

            if len(sn.split2) > 1:
                splits = get_splits(sn.split2, sn.o_idx2, sn.g_idx2)
                if len(splits) == 0 and not in_order(sn.split2):
                    #print sn.split2, 'is not ITG compliant'
                    sn.non_itg_split2 = True
                else:
                    #print 'no reodering in ', sn.split2
                    pass
                for s1, s2, s_idx1, s_idx2, gidx1, gidx2, swaps in splits:
                    #print s1, 'splits ', s2, 'base', sn.split2
                    legal = True
                    head = 0
                    if swaps:
                        #print  gidx1, 'swaps with',  gidx2
                        legal, head = check_for_heads(dep_parse, coe_sentence, gidx1, gidx2, vis_lang)
                    if legal:
                        sn_child = SplitNode(s1, s2, s_idx1, s_idx2, gidx1, gidx2, swaps, head)
                        sn.add_child(sn_child, 2)
                        _stack.append(sn_child)
                    else:
                        print 'blocking illeagal swap', gidx1, gidx2


        #print '******* keep one ********'
        #root_node.keep_one()
        rs = root_node.get_one_derivation(align, rs)
        for r in rs:
            if r[-1].non_itg_split1:
                print r[-1].split1
                non_itg_spans.append(r[-1].split1)
            if r[-1].non_itg_split2:
                print r[-1].split2
                non_itg_spans.append(r[-1].split2)
            
        # swap_rules += [r for r in rs if r[0]]
        for r in rs:
            if r[0]:
                involved_g = set(r[3])
                if involved_g not in split_sets:
                    swap_rules.append(r)
                else:
                    sys.stderr.write('skipping split rule:' + str(r) + '\n')

    return swap_rules, non_itg_spans


if __name__ == '__main__':
    pass
