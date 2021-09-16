#!/usr/bin/env python3

"""
Construction of a loose consensus tree.
"""


__author__ = 'David Schaller'


from tralda.datastructures.Tree import Tree, TreeNode, LCA


def loose_consensus_tree(trees):
    """Compute the loose consensus tree for trees with the same leaf set.
    
    All input trees must be phylogenetic and have the same set of leaf IDs.
    In each tree, the leaf IDs must be unique.
    
    Parameters
    ----------
    trees : sequence of Tree instances
    
    Returns
    -------
    Tree
        The loose consensus tree; None if 'trees' is empty.
        
    Raises
    ------
    TypeError
        In case of input instances that are not of type Tree.
    RuntimeError
        If the sequence contains empty trees or the tree do not share the same
        set of leaves.
        
    References
    ----------
    .. [1] J. Jansson, C. Shen, W.-K. Sung.
       Improved Algorithms for Constructing Consensus Trees.
       In: J. ACM 63, 3, Article 28 (June 2016), 24 pages.
       doi:10.1145/2925985.
    """
    
    LC = LooseConsensusTree(trees)
    return LC.run()


class LooseConsensusTree:
    
    def __init__(self, trees):
        
        _assert_leaf_sets_equal(trees)
        self.trees = trees
    
    
    def run(self):
        
        self.total_contracted = 0
        
        k = len(self.trees)
        if k == 0:
            return None
        elif k == 1:
            return self.trees[0].copy()
        
        T = self.trees[0]
        for j in range(1, k):
            A, x = one_way_compatible(T, self.trees[j],
                                      return_no_of_contractions=True)
            self.total_contracted += x
            T = merge_trees(A, self.trees[j])
        
        for j in range(k):
            T, x = one_way_compatible(T, self.trees[j],
                                      return_no_of_contractions=True)
            self.total_contracted += x
        
        self.T = T
        return self.T


def merge_all(trees):
    """Common refinement for compatible trees with the same leaf set.
    
    All input trees must be phylogenetic and have the same set of leaf IDs.
    In each tree, the leaf IDs must be unique.
    
    Warning: The behavior of the function is undefined if the trees are not
    compatible, i.e., if no common refinement exists.
    
    Parameters
    ----------
    trees : sequence of Tree instances
    
    Returns
    -------
    Tree
        A common refinement of the input trees; None if 'trees' is empty.
    """
    
    _assert_leaf_sets_equal(trees)
    
    k = len(trees)
    if k == 0:
        return None
    elif k == 1:
        return trees[0].copy()
    
    T = trees[0]
    for j in range(1, k):
        T = merge_trees(T, trees[j])
    
    return T


def _assert_leaf_sets_equal(trees):
    
    L = None
        
    for T_i in trees:
        
        if not isinstance(T_i, Tree):
            raise TypeError("not a 'Tree' instance")
            
        if not L:
            L = {v.ID for v in T_i.leaves()}
            if len(L) == 0:
                raise RuntimeError('empty tree in tree list')
        else:
            L2 = {v.ID for v in T_i.leaves()}
            if L != L2:
                raise RuntimeError('trees must have the same leaf IDs')


def _preprocess(T1, T2):
    
    # bijection such that clusters in T1 form sequences os consecutive integers
    f = {l.ID: i for i, l in enumerate(T1.leaves())}
    
    # dict storing the minimal f(x) for each vertex in T2
    m = {}
    for v in T2.postorder():
        m[v] = min(m[c] for c in v.children) if v.children else f[v.ID]
    
    counting_sort = [[] for i in range(len(f))]
    for v in T2.preorder():
        counting_sort[m[v]].append(v)
    sorted_vertices = [v for sublist in counting_sort for v in sublist]
    
    # copy T2 while ordering all children according to counting_sort
    orig_to_new = {}
    for orig in sorted_vertices:
        new = TreeNode(orig.ID, label=orig.label)
        orig_to_new[orig] = new
        if orig.parent:
            orig_to_new[orig.parent].add_child(new)
    T2 = Tree(orig_to_new[T2.root])
    
    # dict storing for each vertex the number edges from the root
    depth = {}
    for v in T2.preorder():
        depth[v] = depth[v.parent] + 1 if v.parent else 0
    
    L_T2 = list(T2.leaves())
    leaf_rank = {l.ID: i for i, l in enumerate(L_T2)}
    start, stop = {}, {}
    for u in T1.postorder():
        if not u.children:
            start[u] = leaf_rank[u.ID]
            stop[u] = leaf_rank[u.ID]
        else:
            start[u] = min(start[c] for c in u.children)
            stop[u] = max(stop[c] for c in u.children)
    
    # vertex in T2 with smallest depth whose leftmost leaf is x
    x_left, leftmost = {}, {}
    # vertex in T2 with smallest depth whose rightmost leaf is x
    x_right, rightmost = {}, {}
    
    for v in T2.postorder():
        if not v.children:
            x_left[v] = v
            leftmost[v] = v
            x_right[v] = v
            rightmost[v] = v
        else:
            cur_leftmost = leftmost[v.children[0]]
            leftmost[v] = cur_leftmost
            x_left[cur_leftmost] = v
            
            cur_rightmost = rightmost[v.children[-1]]
            rightmost[v] = cur_rightmost
            x_right[cur_rightmost] = v
    
    lca = LCA(T2)
    
    return T2, L_T2, lca, depth, start, stop, x_left, x_right


def merge_trees(T1, T2):
    """Common refinement of two compatible trees with the same leaf set.
    
    Both input trees must be phylogenetic and have the same set of leaf IDs.
    In each tree, the leaf IDs must be unique.
    
    Parameters
    ----------
    T1 : Tree
    T2 : Tree
    
    Returns
    -------
    Tree
        A tree whose clusters are the union of the cluster of T1 and T2.
        
    References
    ----------
    .. [1] J. Jansson, C. Shen, W.-K. Sung.
       Improved Algorithms for Constructing Consensus Trees.
       In: J. ACM 63, 3, Article 28 (June 2016), 24 pages.
       doi:10.1145/2925985.
    """
    
    # T2 gets copied in _preprocess, so input trees remain unchanged
    T2, L_T2, lca, depth, start, stop, x_left, x_right = _preprocess(T1, T2)
    
    for u in T1.postorder():
        
        if not u.children:
            continue
        
        a = L_T2[start[u]]
        b = L_T2[stop[u]]
        r_u = lca(a, b)
        
        leftmost_child = r_u.children[0]
        rightmost_child = r_u.children[-1]
        
        d_u = x_left[a] if depth[x_left[a]] > depth[r_u] else leftmost_child
        e_u = x_right[b] if depth[x_right[b]] > depth[r_u] else rightmost_child
        
        if d_u is leftmost_child and e_u is rightmost_child:
            continue
        
        c = TreeNode(-1)
        depth[c] = depth[r_u] + 1
        if d_u is not leftmost_child:
            x_left[a] = c
        if e_u is not rightmost_child:
            x_right[b] = c
        r_u.add_child_right_of(c, e_u)
        
        c_children = r_u.child_subsequence(d_u, e_u)
        for child in c_children:
            c.add_child(child)
    
    return T2


def one_way_compatible(T1, T2, return_no_of_contractions=False):
    """Remove all clusters in a tree T1 that are incompatible with T2.
    
    Both input trees must be phylogenetic and have the same set of leaf IDs.
    In each tree, the leaf IDs must be unique.
    
    Parameters
    ----------
    T1 : Tree
    T2 : Tree
    
    Returns
    -------
    Tree
        A copy of T1 with all clusters removed (i.e. the corresponding edges
        are contracted) that are incompatible with T2.
        
    References
    ----------
    .. [1] J. Jansson, C. Shen, W.-K. Sung.
       Improved Algorithms for Constructing Consensus Trees.
       In: J. ACM 63, 3, Article 28 (June 2016), 24 pages.
       doi:10.1145/2925985.
    """
    
    # T2 gets copied in _preprocess, so input trees remain unchanged
    T2, L_T2, lca, depth, start, stop, x_left, x_right = _preprocess(T1, T2)
    
    # size of all cluster in T1
    size = {}
    
    # edges uv such that L(T1(v)) is a cluster that is not compatible with T2
    bad_edges = []
    
    for u in T1.postorder():
        
        size[u] = sum(size[c] for c in u.children) if u.children else 1
        
        if not u.children:
            continue
        
        a = L_T2[start[u]]
        b = L_T2[stop[u]]
        r_u = lca(a, b)
        
        leftmost_child = r_u.children[0]
        rightmost_child = r_u.children[-1]
        
        d_u = x_left[a] if depth[x_left[a]] > depth[r_u] else leftmost_child
        e_u = x_right[b] if depth[x_right[b]] > depth[r_u] else rightmost_child
        
        if ((d_u.parent is not r_u) or (e_u.parent is not r_u) or
            (size[u] != stop[u] - start[u] + 1)):
            bad_edges.append((u.parent, u))
    
    T = T1.copy()
    T.contract(bad_edges)
    
    if return_no_of_contractions:
        return T, len(bad_edges)
    else:
        return T

            
if __name__ == '__main__':
    
    import random
    
    tree = Tree.random_tree(10, binary=True)
    partial_trees = []
    for i in range(10):
        T_i = tree.copy()
        edges = []
        for u, v in T_i.inner_edges():
            if random.random() < 0.8:
                edges.append((u,v))
        T_i.contract(edges)
        partial_trees.append(T_i)
    
    T1 = partial_trees[0]
    T2 = partial_trees[1]
    # T = merge_trees(T1, T2)
    # T = loose_consensus_tree([T1, T2])
    T = loose_consensus_tree(partial_trees)
    print(T1.to_newick())
    print(T2.to_newick())
    print(T.to_newick())
    print(T.is_refinement(T1))
    print(T.is_refinement(T2))