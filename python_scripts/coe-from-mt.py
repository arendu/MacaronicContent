#!/usr/bin/env python
__author__ = 'arenduchintala'
import codecs
from optparse import OptionParser
from itertools import groupby, product
from collection_of_edits import Sentence, Node, Graph, EN_LANG, DE_LANG, START, END, get_edges, Swap
from pets import get_swap_rules, get_split_sets, in_order
import json
import sys
import operator
import itertools

reload(sys)
sys.setdefaultencoding('utf-8')
sys.stdin = codecs.getreader('utf-8')(sys.stdin)
sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
sys.stdout.encoding = 'utf-8'

VIS_LANG = 'de'
INPUT_LANG = 'de'
USE_SPLIT = False


def check_initial_orders(sent_obj, vis_lang):
    vis_toks = []
    if vis_lang == 'de':
        vis_toks = sent_obj.en.split()
    else:
        vis_toks = sent_obj.de.split()

    vis_nodes = []
    for g in sent_obj.graphs:
        for n in g.nodes:
            if n.visible:
                vis_nodes.append((n.visible_order, n.s))

    vis_nodes.sort()
    vis_node_toks = [n for i, n in vis_nodes]
    sys.stderr.write('en: ' + sent_obj.en + '\n')
    sys.stderr.write(' '.join(vis_toks) + '\n')
    sys.stderr.write(' '.join(vis_node_toks) + '\n')
    vis_node_toks = [v.split('~~~') for v in vis_node_toks]
    vis_node_toks= sum(vis_node_toks, []) #flatten list of lists
    #[item for sublist in vis_node_toks for item in sublist]
    #print vis_node_toks
    #print vis_toks
    for v_n_tok, v_tok in zip(vis_node_toks, vis_toks):
        sys.stderr.write(v_n_tok + ' vs ' + v_tok + '\n')
        assert v_n_tok == v_tok
    return True


def logit(str, priority=10):
    if priority > 5:
        sys.stderr.write(str)


def get_contiguous(lst):
    ranges = []
    for k, g in groupby(enumerate(lst), lambda (i, x): i - x):
        group = map(operator.itemgetter(1), g)
        ranges.append((group[0], group[-1]))
    return ranges


def swap_key(k, sw):
    assert isinstance(k, int)
    assert isinstance(sw, set)
    l = [i for i in sw]
    l.append(k)
    l.sort()
    return tuple(l)


def get_lr(input_list, output_list):
    input_unique = [i[0] for i in groupby(input_list)]
    output_unique = [i[0] for i in groupby(output_list)]
    input_lr = {}
    for idx, i in enumerate(input_unique):
        l = input_unique[idx - 1] if 0 < idx  else '**'
        r = input_unique[idx + 1] if idx < len(input_unique) - 1 else '**'
        input_lr[i] = (l, r)
    output_lr = {}
    for idx, i in enumerate(output_unique):
        l = output_unique[idx - 1] if 0 < idx else '**'
        r = output_unique[idx + 1] if idx < len(output_unique) - 1 else '**'
        output_lr[i] = (l, r)
    return input_lr, output_lr


def detect_split_reorderings(input_tok_group, output_tok_group):
    split_inp = {}
    split_out = {}
    split_orderings = {}
    separatee_inp = []
    separator_inp = []
    separatee_out = []
    separator_out = []
    for i in set(input_tok_group):
        tmp = [idx_x for idx_x, x in enumerate(input_tok_group) if x == i]
        c = get_contiguous(tmp)
        if len(c) == 2:
            c0 = c[0][1]
            c1 = c[1][0]
            middle_idxs = range(c0 + 1, c1)
            interrupting_group = [input_tok_group[mi] for mi in middle_idxs]
            separatee_inp.append(i)
            separator_inp.append(interrupting_group)
            # print 'discontiguous input', c, i, interrupting_group
            sp_in_out = output_tok_group.index(i)
            interrupting_group_lr = [('left' if (output_tok_group.index(ig) < sp_in_out)  else 'right') for ig in
                    interrupting_group]
            split_inp[i] = (interrupting_group, interrupting_group_lr)
            involved_graphs = set((interrupting_group + [i]))
            # o1 = [ix for ix in output_tok_group if ix in involved_graphs]
            # o2 = [ix for ix in input_tok_group if ix in involved_graphs]
            o1 = [ix for ix in input_tok_group if ix in involved_graphs]
            o2 = [ix for ix in output_tok_group if ix in involved_graphs]
            # assert len(o1) != len(o2)  #todo: must address this exception
            if len(o1) > len(o2):
                split_orderings[i] = {'split_ordering': o1, 'unsplit_ordering': o2}
            else:
                split_orderings[i] = {'split_ordering': o1, 'unsplit_ordering': o2}


        elif len(c) == 1:
            pass
        # print 'contiguous input'
    else:
        pass

    for i in set(output_tok_group):
        tmp = [idx_x for idx_x, x in enumerate(output_tok_group) if x == i]
        c = get_contiguous(tmp)
        if len(c) == 2:
            c0 = c[0][1]
            c1 = c[1][0]
            middle_idxs = range(c0 + 1, c1)
            interrupting_group = [output_tok_group[mi] for mi in middle_idxs]
            separatee_out.append(i)
            separator_out.append(interrupting_group)
            # print 'discontiguous output', c, i, interrupting_group
            sp_in_inp = input_tok_group.index(i)
            interrupting_group_lr = [('left' if (input_tok_group.index(ig) < sp_in_inp) else 'right') for ig in
                    interrupting_group]
            split_out[i] = (interrupting_group, interrupting_group_lr)

            involved_graphs = set((interrupting_group + [i]))
            o1 = [ix for ix in output_tok_group if ix in involved_graphs]
            o2 = [ix for ix in input_tok_group if ix in involved_graphs]
            # assert len(o1) != len(o2) #todo: must address this exception
            if len(o1) > len(o2):
                split_orderings[i] = {'split_ordering': o1, 'unsplit_ordering': o2}
            else:
                split_orderings[i] = {'split_ordering': o1, 'unsplit_ordering': o2}
        elif len(c) == 1:
            pass
        # print 'contiguous ouput'
    else:
        pass

    return split_inp, split_out, split_orderings


def swap_notation(i, swap_i, swap_o):
    if i in swap_i:
        return i, swap_o[swap_i.index(i)]
    elif i in swap_o:
        return swap_i[swap_o.index(i)], i
    else:
        return i


def check_symmetric(wa_list):
    inp_wa, out_wa = make_inp_out(wa_list)
    inp_wa_sym = check_wa_dict(inp_wa)
    out_wa_sym = check_wa_dict(out_wa)
    return inp_wa_sym and out_wa_sym


def check_wa_dict(wa_dict):
    for k, v in wa_dict.items():
        if len(v) > 1:
            for v_ind in v:
                for v_all in wa_dict.values():
                    if v_ind in v_all and v_all is not v:
                        return False
    return True


def make_inp_out(wa_list):
    inp_wa = {}
    out_wa = {}
    for inp_a, out_a in wa_list:
        tmp = inp_wa.get(tuple([inp_a]), set([]))
        tmp = set(list(tmp))
        tmp.add(out_a)
        inp_wa[tuple([inp_a])] = tuple(list(tmp))
        tmp = out_wa.get(tuple([out_a]), set([]))
        tmp = set(list(tmp))
        tmp.add(inp_a)
        out_wa[tuple([out_a])] = tuple(list(tmp))

    return inp_wa, out_wa


def get_coverage(wa_list, original_wa_list):
    original_inp = set([i[0] for i in original_wa_list])
    original_out = set([i[1] for i in original_wa_list])
    current_inp = set([i[0] for i in wa_list])
    current_out = set([i[1] for i in wa_list])
    return len(original_inp - current_inp) + len(original_out - current_out)


def insert_epsilon_edge(wa_original, inp_phrase, out_phrase):
    wa = [a for a in wa_original]
    inp_cov = [0] * len(inp_phrase)
    out_cov = [0] * len(out_phrase)
    inp_pos_ratio = [float(idx) / len(inp_phrase) for idx, i in enumerate(inp_phrase)]
    out_pos_ratio = [float(idx) / len(out_phrase) for idx, i in enumerate(out_phrase)]
    while 0 in inp_cov or 0 in out_cov:
        for i, o in wa:
            inp_cov[i] = 1
            out_cov[o] = 1
        for i_idx, (pos_ratio, ic) in enumerate(zip(inp_pos_ratio, inp_cov)):
            if ic == 0:
                out_pos_ratio_diff = [(abs(pos_ratio - pr), o_idx) for o_idx, pr in enumerate(out_pos_ratio)]
                out_pos_ratio_diff.sort()
                best_out_alignment_idx = out_pos_ratio_diff[0][1]
                wa.append((i_idx, best_out_alignment_idx))
        for i, o in wa:
            inp_cov[i] = 1
            out_cov[o] = 1
        for o_idx, (pos_ratio, oc) in enumerate(zip(out_pos_ratio, out_cov)):
            if oc == 0:
                inp_pos_ratio_diff = [(abs(pos_ratio - pr), i_idx) for i_idx, pr in enumerate(inp_pos_ratio)]
                inp_pos_ratio_diff.sort()
                best_inp_alignment_idx = inp_pos_ratio_diff[0][1]
                wa.append((best_inp_alignment_idx, o_idx))
        for i, o in wa:
            inp_cov[i] = 1
            out_cov[o] = 1
    return wa


def make_symmetric(wa_list):
    _stack = []
    _stack.append((0, wa_list))
    while len(_stack) > 0:
        _stack.sort()
        curr_coverage, curr_wa_list = _stack.pop(0)
        if check_symmetric(curr_wa_list):
            return curr_coverage, curr_wa_list
        else:
            for i in range(0, len(curr_wa_list)):
                copy_wa_list = [item for idx, item in enumerate(curr_wa_list) if idx != i]
                # print 'removing an item', copy_wa_list, ' form ', curr_wa_list
                _stack.append((get_coverage(copy_wa_list, wa_list), copy_wa_list))
    return 0, []


def remove_subset(d):
    # print 'checking remove subset', d
    del_d = set([])
    for k, v in d.items():
        set_k = set(list(k))
        set_v = set(list(v))
        for sk, sv in d.items():
            set_sk = set(list(sk))
            set_sv = set(list(sv))
            # print 'compare', set_k, set_sk
            if set_k != set_sk and set_k.issubset(set_sk):
                del_d.add(tuple(set_k))
    # print 'delete', del_d, 'in ', d.keys()
    return del_d


def untangle_wa(wa_list):
    inp_wa_2_out_wa = {}
    out_wa_2_inp_wa = {}
    merged = {}
    for inp_a, out_a in wa_list:
        tmp = inp_wa_2_out_wa.get(tuple([inp_a]), set([]))
        tmp.add(out_a)
        inp_wa_2_out_wa[tuple([inp_a])] = tmp
        tmp = out_wa_2_inp_wa.get(tuple([out_a]), set([]))
        tmp.add(inp_a)
        out_wa_2_inp_wa[tuple([out_a])] = tmp

    # print 'before'

    same = False
    p_r_i = None
    p_r_o = None
    while not same:
        del_inp = set([])
        del_out = set([])
        for ko, vi in out_wa_2_inp_wa.items():
            for v in vi:
                update1 = inp_wa_2_out_wa.get(tuple([v]), set([]))
                update2 = inp_wa_2_out_wa.get(tuple(vi), set([]))
                inp_wa_2_out_wa[tuple(vi)] = update1.union(update2)
                del_inp.add(tuple([v]))
        for ki, vo in inp_wa_2_out_wa.items():
            for v in vo:
                update1 = out_wa_2_inp_wa.get(tuple([v]), set([]))
                update2 = out_wa_2_inp_wa.get(tuple(vo), set([]))
                out_wa_2_inp_wa[tuple(vo)] = update1.union(update2)
                del_out.add(tuple([v]))
        # print 'after'
        r_i = remove_subset(inp_wa_2_out_wa)
        r_o = remove_subset(out_wa_2_inp_wa)
        if r_i == p_r_i and r_o == p_r_o:
            same = True
        else:
            same = False
        p_r_i = r_i
        p_r_o = r_o



    # print 'deleting subsets'
    for rem_ro in p_r_o:
        del out_wa_2_inp_wa[rem_ro]
    for rem_ri in p_r_i:
        del inp_wa_2_out_wa[rem_ri]

    for k, v in inp_wa_2_out_wa.items():
        inp_wa_2_out_wa[k] = tuple(list(v))
    return inp_wa_2_out_wa


def make_edges(from_nodes, to_nodes):
    edges = []
    for fn in from_nodes:
        for tn in to_nodes:
            edges += get_edges(fn, tn)
            # print fn.s, tn.s
    return edges


def make_edges_with_intermediate_nodes(from_nodes, to_nodes, intermediate, graph):
    edges = []
    # import pdb



    has_intermediate = False
    if (len(to_nodes) == 1 and len(from_nodes) == 1) or (len(to_nodes) > 1 and len(from_nodes) == 1):
        for f, t in product(from_nodes, to_nodes):
            int_tok = intermediate.get((f.s, t.s), None)
            repeat = int_tok in [i.s for i in from_nodes]
            has_intermediate = (int_tok is not None and int_tok != 'NULL' and f.s != t.s) or has_intermediate
            has_intermediate = has_intermediate and (not repeat)

    if has_intermediate:
        for f, t in product(from_nodes, to_nodes):
            int_tok = intermediate.get((f.s, t.s), None)
            if int_tok is None or int_tok == 'NULL' or f.s == t.s:
                int_tok = f.s  # why force this?
            else:
                pass
            logit('int:' + int_tok + ' in:' + f.s + '-' + t.s + '\n')
            int_node = f.makecopy()
            int_node.id = len(graph.nodes)
            int_node.s = int_tok
            int_node.to_en = True
            int_node.to_de = True
            int_node.en_id = int_node.en_id if int_node.en_id is not None else t.en_id
            int_node.de_id = int_node.de_id if int_node.de_id is not None else t.de_id
            graph.nodes.append(int_node)
            edges += get_edges(f, int_node)
            edges += get_edges(int_node, t)
    else:
        for f, t in product(from_nodes, to_nodes):
            edges += get_edges(f, t)
    return edges


def get_output_phrase_as_spans(output_phrases):
    op_spans = []
    st_idx = 0
    end_idx = 0
    for op in output_phrases:
        l = len(op.split()) - 1
        end_idx = st_idx + l
        op_spans.append((st_idx, end_idx))
        st_idx = end_idx + 1
    return op_spans


def get_groups_that_external_reorder(input_tok_group, output_tok_group):
    reordering_groups = []
    for i_idx, inp_group in enumerate(input_tok_group):
        o_idxes = [o_idx for o_idx, out_group in enumerate(output_tok_group) if out_group == inp_group]
        if len(o_idxes) > 1:
            reordering_groups.append(inp_group)
        else:
            inp_group_left = [ig for igx, ig in enumerate(input_tok_group) if igx == i_idx - 1]
            inp_group_right = [ig for igx, ig in enumerate(input_tok_group) if igx == i_idx + 1]
            out_group_left = [og for ogx, og in enumerate(output_tok_group) if ogx == o_idxes[0] - 1]
            out_group_right = [og for ogx, og in enumerate(output_tok_group) if ogx == o_idxes[0] + 1]
            if inp_group_left == out_group_left and inp_group_right == out_group_right:
                pass
            else:
                reordering_groups.append(inp_group)
    return reordering_groups


def propagate_split_info(sent):
    for g in sent.graphs:
        if g.splits:
            interacts_with = g.separators
            for iw in interacts_with:
                g_other = sent.get_graph_by_id(iw)
                g_other.is_separator = True
                set(interacts_with).add(g.id)
                set(interacts_with).remove(g_other.id)
                g_other.split_iteraction = list(interacts_with)


def find_nearest_node_with_property(n, direction, graph):
    if direction == DE_LANG:
        de_n = Node(None, None, None, None, None, None)
        while de_n.de_id is None:
            de_neighbors = graph.get_neighbor_nodes(n, DE_LANG)
            de_n = de_neighbors[0]


def propagate(graph):
    graph.set_visibility(VIS_LANG)
    # graph.cognate_visibility(VIS_LANG)
    for n in graph.nodes:
        if n.de_id is None:
            de_n = n
            while de_n.de_id is None:
                de_neighbors = graph.get_neighbor_nodes(de_n, DE_LANG)
                de_n = de_neighbors[0]
            assert de_n.de_id is not None
            n.de_id = de_n.de_id

        if n.en_id is None:
            en_n = n
            while en_n.en_id is None:
                en_neighbors = graph.get_neighbor_nodes(en_n, EN_LANG)
                en_n = en_neighbors[0]
            assert en_n.en_id is not None
            n.en_id = en_n.en_id


def min_visible_word_position(graph, vis_lang):
    n_ids = []
    for n in graph.nodes:
        if n.visible and n.lang == vis_lang:
            if vis_lang == EN_LANG:
                n_ids.append(n.en_id)
            else:
                n_ids.append(n.de_id)
    n_ids.sort()
    return n_ids[0]


def sort_groups_by_lang(graphs, vis_lang):
    graph_tuple = [(min_visible_word_position(g, vis_lang), g) for g in graphs]
    graph_tuple.sort()
    graph_tuple = [g for mv, g in graph_tuple]
    graph_by_ids = []
    for sorted_g_idx, g in enumerate(graph_tuple):
        g.initial_order = sorted_g_idx
        g.external_reorder_by = vis_lang
        graph_by_ids.append((g.initial_order, g))
    graph_by_ids.sort()
    graphs = [g for gio, g in graph_by_ids]
    return graphs


def get_dep_parse(path):
    dep_parses = []
    for dp in codecs.open(path, 'r', 'utf-8').read().split('\n\n'):
        if dp.strip() != u'':
            dep_parse = []
            for l in dp.strip().split('\n'):
                l = l.strip()[4:-1]
                [from_dep, to_dep] = l.split(',')[:2]
                dep_parse.append((from_dep, to_dep))
            dep_parses.append(dep_parse)
    return dep_parses


def compute_vocab_histogram(sentence_list):
    hist = {}
    for line in sentence_list:
        for word in line.split():
            c = hist.get(word.lower(), 0.0) + 1.0
            hist[word.lower()] = c
    m = max(hist.values())
    hist = dict((k, v / m) for k, v in hist.iteritems())
    return hist


if __name__ == '__main__':
    opt = OptionParser()

    opt.add_option('-i', dest='input_mt', default='')
    opt.add_option('-s', dest='split_string', default='')
    opt.add_option('-o', dest='output_mt', default='')
    opt.add_option('-e', dest='intermediate', default='')
    # opt.add_option('-p', dest='input_parse', default='../web/newstest2013/newstest2013.input.tok.1.parsed')
    opt.add_option('-p', dest='input_parse', default='')
    opt.add_option('-d', dest='is_demo', default='0')
    opt.add_option('--out', dest='output_stem', default='')
    # opt.add_option('--e2f', dest='e2f', default='../web/newstest2013/lex1.e2f.small')
    # opt.add_option('--f2e', dest='f2e', default='../web/newstest2013/lex1.f2e.small')
    (options, _) = opt.parse_args()
    if options.input_mt == '' or options.output_mt == '' or options.input_parse == '' or options.output_stem == '':
        logit(
                'Usage: python coe-from-mt.py -i INPUT_MT -o OUTPUT_MT -e INTERMEDIATE_EDGES -p INPUT_MT_PARSED -s SPLIT_STRING --out OUTPUT_STEM\n',
                10)
        exit(-1)
    else:
        pass
    USE_SPLIT = False
    is_demo = int(options.is_demo) == 1
    input_parsed = get_dep_parse(options.input_parse)
    input_mt = codecs.open(options.input_mt, 'r', 'utf-8').readlines()
    input_histogram = compute_vocab_histogram(input_mt)
    output_mt = codecs.open(options.output_mt, 'r', 'utf-8').readlines()
    intermediate_nodes = {}
    try:
        for l in codecs.open(options.intermediate, 'r', 'utf-8').readlines():
            w1, w2, inter = l.strip().split()
            intermediate_nodes[(w1, w2)] = inter
    except IOError:
        logit("no intermediate edges file found...skipping\n", 10)
    assert len(input_mt) == len(output_mt)
    sent_idx = 0
    eps_word_alignment = 0
    reorder_failed = []
    all_coe_sentences = []
    coe_sentences = []
    sentences_used = []
    for sent_idx, (input_line, output_line, input_parse) in enumerate(zip(input_mt, output_mt, input_parsed)[:]):
        logit('len all coe ' + str(len(all_coe_sentences)) + ' len coe ' + str(
            len(coe_sentences)) + ' using split: ' + str(USE_SPLIT) + 'split string:' + options.split_string + '\n')
        logit('SENT' + str(sent_idx) + '\n')
        input_sent = input_line.strip().split()
        sentences_used.append(str(sent_idx) + "\t" + input_line.strip())
        output_items = output_line.strip().split('|')
        output_phrases = [oi.strip() for idx, oi in enumerate(output_items) if idx % 2 == 0 and oi.strip() != '']
        output_sent = ' '.join(output_phrases).split()
        output_spans = get_output_phrase_as_spans(output_phrases)
        output_meta = [tuple(om.split(',wa=')) for idx, om in enumerate(output_items) if idx % 2 != 0]
        input_spans = [tuple([int(i) for i in om[0].split('-')]) for om in output_meta]
        wa_per_span = [[tuple([int(i) for i in a.split('-')]) for a in om[1].split()] for om in output_meta]
        input_tok_group = [-1] * len(input_sent)
        output_tok_group = [-1] * len(output_sent)

        logit('input sent:' + ' '.join(input_sent) + '\n')
        logit('output sent:' + ' '.join(output_sent) + '\n')
        coe_sentence = Sentence(sent_idx, ' '.join(input_sent), ' '.join(output_sent), None)
        coe_sentence.initial_order_by = VIS_LANG

        assert len(wa_per_span) == len(input_spans) == len(output_spans)
        phrase_dict = {}
        input_coverage = [0] * len(input_sent)
        group_idx = 0

        for idx, (out_span, inp_span, wa) in enumerate(zip(output_spans, input_spans, wa_per_span)):
            out_phrase = output_sent[out_span[0]:out_span[1] + 1]
            inp_phrase = input_sent[inp_span[0]:inp_span[1] + 1]
            print '\t phrases:', inp_phrase, '-', out_phrase
            print '\t phrase spans:', inp_span, '-', out_span
            print '\twa:', wa
            i_phrase_wa = [i for i, j in wa]
            o_phrase_wa = [j for i, j in wa]
            true_i_phrase = [tok for i, tok in enumerate(inp_phrase) if i in i_phrase_wa]
            true_o_phrase = [tok for i, tok in enumerate(out_phrase) if i in o_phrase_wa]
            print '\t true phrases:', true_i_phrase, '-', true_o_phrase

            wa_no_null = wa  # insert_epsilon_edge(wa, true_i_phrase, true_o_phrase)
            sym_coverage, sym_wa = make_symmetric(wa_no_null)
            assert sym_coverage == 0
            untangle = untangle_wa(sym_wa)
            final_groups = {}
            for iu in sorted(untangle):
                ou = untangle[iu]
                if len(iu) > 1:
                    assert len(ou) == 1  # or (len(iu) == 2 and len(ou) == 2)
                    pass
                if len(ou) > 1:
                    assert len(iu) == 1  # or (len(iu) == 2 and len(ou) == 2)
                    pass
                final_groups[group_idx] = (iu, ou, inp_span, out_span)
                coe_graph = Graph(group_idx)
                to_nodes = []
                node_idx = 0
                for iu_idx in iu:
                    assert inp_phrase[iu_idx] == input_sent[inp_span[0] + iu_idx]
                    input_coverage[inp_span[0] + iu_idx] = 1
                    input_tok_group[inp_span[0] + iu_idx] = group_idx
                    n = Node(node_idx, input_sent[inp_span[0] + iu_idx], None, inp_span[0] + iu_idx, DE_LANG,
                            VIS_LANG == DE_LANG, True, False, False)
                    n.frequency = input_histogram[n.s.lower()]
                    node_idx += 1
                    to_nodes.append(n)

                from_nodes = []
                for ou_idx in ou:
                    assert out_phrase[ou_idx] == output_sent[out_span[0] + ou_idx]
                    output_tok_group[out_span[0] + ou_idx] = group_idx
                    n = Node(node_idx, output_sent[out_span[0] + ou_idx], out_span[0] + ou_idx, None, EN_LANG,
                            VIS_LANG == EN_LANG, False, True, False)
                    node_idx += 1
                    from_nodes.append(n)

                if len(from_nodes) > 1:
                    assert len(to_nodes) == 1  # or (len(iu) == 2 and len(ou) == 2)
                    pass
                if len(to_nodes) > 1:
                    assert len(from_nodes) == 1  # or (len(iu) == 2 and len(ou) == 2)
                    pass
                coe_graph.nodes = from_nodes + to_nodes
                coe_graph.edges = make_edges(from_nodes, to_nodes)
                coe_graph.edges = make_edges_with_intermediate_nodes(from_nodes, to_nodes,
                        intermediate=intermediate_nodes, graph=coe_graph)
                coe_graph.compute_edit_distance()
                coe_sentence.graphs.append(coe_graph)
                group_idx += 1
                # pprint(final_groups)
                # pdb.set_trace()
        if 0 in input_coverage:
            eps_word_alignment += 1
            assert 0 not in input_coverage

        coe_sentence.graphs = sort_groups_by_lang(coe_sentence.graphs, VIS_LANG)
        logit(' '.join([str(i) for i in input_tok_group]) + '\n')
        logit(' '.join([str(i) for i in output_tok_group]) + '\n')

        split_inp, split_out, split_orderings = detect_split_reorderings(input_tok_group,output_tok_group)
        split_sets = get_split_sets(split_inp, split_out)
        swap_rules, non_itg_spans = get_swap_rules(coe_sentence, input_tok_group, output_tok_group, input_parse, split_sets, VIS_LANG)
        if len(swap_rules) > 0:
            for sr in swap_rules:
                logit('swaps-pets:' + str(sr) + '\n')
        else:
            logit("no swap rules...\n")
            if in_order(input_tok_group):
                pass
            else:
                reorder_failed += [coe_sentence]
                logit("could not reorder sentence...")

        split_inp_str = ' '.join([str(i) + "-" + ','.join([str(k) for k in j[0]]) for i, j in split_inp.items()])
        logit('split inp:' + split_inp_str + '\n')
        split_out_str = ' '.join([str(i) + "-" + ','.join([str(k) for k in j[0]]) for i, j in split_out.items()])
        logit('split out:' + split_out_str + '\n')
        if len(split_inp) or len(split_out):
            pass  # pdb.set_trace()
        swap_objs = []
        for sr in swap_rules:
            s_obj = Swap()
            s_obj.graphs = sr[1]
            s_obj.other_graphs = sr[2]
            s_obj.head = sr[4]
            swap_objs.append(s_obj)

        for g in coe_sentence.graphs:
            g.er = True
            for so in swap_objs:
                if g.id in so.graphs or g.id in so.other_graphs:
                    # print 'there!', g.id
                    if VIS_LANG == 'de':
                        g.swaps = True
                        g.swap_toward_en.append(so.make_copy())
                    else:
                        g.swaps = True
                        g.swap_toward_de.append(so.make_copy())
                else:
                    # print 'not there', g.id
                    pass
            if g.id in split_out.keys():
                # output language is split
                g.splits = True
                g.separators = list(set(split_out[g.id][0]))
                g.separator_positions = split_out[g.id][1]
                if INPUT_LANG == 'en':
                    g.split_order_by_de = split_orderings[g.id]['split_ordering']
                    g.split_order_by_en = split_orderings[g.id]['unsplit_ordering']
                else:
                    g.split_order_by_de = split_orderings[g.id]['unsplit_ordering']
                    g.split_order_by_en = split_orderings[g.id]['split_ordering']
                # g.split_ordering = split_orderings[g.id]['split_ordering']
                # g.unsplit_ordering = split_orderings[g.id]['unsplit_ordering']
                g.split_to = 'de' if VIS_LANG == 'de' else 'en'
                # if VIS_LANG == 'de':  # de is the input language and de is the visible language
                # g.currently_split = False
                # else:
                # g.currently_split = True

            if g.id in split_inp.keys():
                # input language is split
                g.splits = True
                g.separators = list(set(split_inp[g.id][0]))
                g.separator_positions = split_inp[g.id][1]
                if INPUT_LANG == 'en':
                    g.split_order_by_en = split_orderings[g.id]['split_ordering']
                    g.split_order_by_de = split_orderings[g.id]['unsplit_ordering']
                else:
                    g.split_order_by_en = split_orderings[g.id]['unsplit_ordering']
                    g.split_order_by_de = split_orderings[g.id]['split_ordering']
                # g.split_ordering = split_orderings[g.id]['split_ordering']
                # g.unsplit_ordering = split_orderings[g.id]['unsplit_ordering']
                g.split_to = 'de' if VIS_LANG == 'en' else 'en'
                # if VIS_LANG == 'de':  # de is the input language and de is the visible language
                # g.currently_split = True
                # else:
                # g.currently_split = False

            for n in g.nodes:
                if n.lang == EN_LANG:
                    if n.s == output_sent[n.en_id]:
                        # n.en_left = [START] + output_tok_group[:n.en_id]
                        # n.en_left.reverse()
                        # n.en_right = output_tok_group[n.en_id + 1:] + [END]
                        pass
                if n.lang == DE_LANG:
                    if n.s == input_sent[n.de_id]:
                        # n.de_left = [START] + input_tok_group[:n.de_id]
                        # n.de_left.reverse()
                        # n.de_right = input_tok_group[n.de_id + 1:] + [END]
                        pass
            propagate(g)

            for n in g.nodes:
                assert n.en_id is not None and n.de_id is not None

        coe_sentence.set_initial_node_orders(VIS_LANG)
        print non_itg_spans, 'HERE'
        for non_itg_span in non_itg_spans:
            coe_sentence.merge_graphs(non_itg_span)
        #TODO: fix this hard coded part!!!
        propagate_split_info(coe_sentence)
        check_initial_orders(coe_sentence, VIS_LANG)
        # logit('done sent' + str(sent_idx) + '\n')

        json_sentence_str = json.dumps(coe_sentence, indent=4, sort_keys=True)
        coe_sentences.append(' '.join(json_sentence_str.split()))
    if len(coe_sentences) > 0:
        all_coe_sentences.append(coe_sentences)
    logit('done\n' + str(len(reorder_failed) + eps_word_alignment) + ' errors\n', priority=10)
    for cs in reorder_failed:
        print 'failed:', cs.en, cs.de
    # FLATTEN THE LIST
    all_coe_sentences = list(itertools.chain.from_iterable(all_coe_sentences))
    all_json_sent_str = json.dumps(all_coe_sentences, indent=4, sort_keys=True)
    f = codecs.open(options.output_stem + '.json', 'w', 'utf8')
    f.write(all_json_sent_str)
    f.flush()
    f.close()
    logit('size:' + str(len(all_coe_sentences)) + '\n', priority=10)
    main_coe_sentences = all_coe_sentences[:-1]
    preview_coe_sentences = all_coe_sentences[-1:]
    main_output = '\n'.join(['var json_str_arr = ' + str(main_coe_sentences), 'module.exports.Story1 = json_str_arr'])
    preview_output = '\n'.join(
            ['var json_str_arr = ' + str(preview_coe_sentences), 'module.exports.Preview = json_str_arr'])
    main_sentences = '\n'.join(sentences_used[:-1])
    preview_sentences = '\n'.join(sentences_used[-1:])
    f = codecs.open(options.output_stem + '.state', 'w', 'utf8')
    f.write('\n'.join(main_coe_sentences))
    f.flush()
    f.close()
    f = codecs.open(options.output_stem + '.preview.state', 'w', 'utf8')
    f.write('\n'.join(preview_coe_sentences))
    f.flush()
    f.close()
    f = codecs.open(options.output_stem + '.js', 'w', 'utf8')
    f.write(main_output)
    f.flush()
    f.close()
    f = codecs.open(options.output_stem + '.sent', 'w', 'utf8')
    f.write(main_sentences)
    f.flush()
    f.close()
    f = codecs.open(options.output_stem + '.preview.js', 'w', 'utf8')
    f.write(preview_output)
    f.flush()
    f.close()
    f = codecs.open(options.output_stem + '.preview.sent', 'w', 'utf8')
    f.write(preview_sentences)
    f.flush()
    f.close()

