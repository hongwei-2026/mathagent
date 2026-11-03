from mathagent.lattice.graph import GraphStore, Node, NodeKind, NodeStatus, ResearchGraph


def test_graph_admit_and_frontier(tmp_path):
    g = ResearchGraph(project_id="demo")
    t = g.add(Node.new(NodeKind.TARGET, "prove X"))
    c = g.add(Node.new(NodeKind.CONJECTURE, "lemma Y"))
    c.score = 0.9
    g.link(t.id, c.id, "depends")
    g.admit_lemma("Y holds", certificate="sympy", parent_id=c.id)
    assert any(n.kind == NodeKind.LEMMA and n.status == NodeStatus.CERTIFIED for n in g.nodes.values())
    store = GraphStore(root=tmp_path)
    path = store.save(g)
    assert path.exists()
    loaded = store.load("demo")
    assert loaded is not None
    assert loaded.summary()


def test_frontier_orders_by_score():
    g = ResearchGraph(project_id="f")
    a = g.add(Node.new(NodeKind.CONJECTURE, "low"))
    a.score = 0.1
    b = g.add(Node.new(NodeKind.CONJECTURE, "high"))
    b.score = 0.95
    assert g.frontier(1)[0].statement == "high"
