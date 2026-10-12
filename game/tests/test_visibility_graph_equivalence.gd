extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var failures: Array=[]
var checks: int=0
func distance(map,a: Dictionary,b: Dictionary) -> float:
	var best: float=absf(float(a.s)-float(b.s)) if a.edge==b.edge else INF
	var first: Dictionary=map.edges[a.edge];var second: Dictionary=map.edges[b.edge]
	for start in [first.from,first.to]:
		for finish in [second.from,second.to]:
			var source_cost: float=float(a.s) if start==first.from else float(first.length)-float(a.s)
			var target_cost: float=float(b.s) if finish==second.from else float(second.length)-float(b.s)
			best=minf(best,source_cost+float(map.shortest_nodes(start,finish).distance)+target_cost)
	return best
func run():
	var db=Data.new()
	for map_id in ["map.01.01","map.01.07","map.01.11","map.01.04","map.01.12","map.01.06"]:
		var s=Simulation.new(db);s.start({"map":map_id,"faction":"yin","enemy":"mo"})
		s.units.clear()
		for base in s.bases:base.hp=0
		var scout=s.spawn("unit.yin.axe",0,20)
		for source_edge in s.map.edges:
			for fraction in [.2,.5,.8]:
				s.map.apply_anchor(scout,s.map.anchor(source_edge,s.map.edges[source_edge].length*fraction));s.visibility.refresh()
				for destination_edge in s.map.edges:
					for t in [.1,.4,.7,.9]:
						var target: Dictionary=s.map.anchor(destination_edge,s.map.edges[destination_edge].length*t)
						var expected: bool=distance(s.map,scout,target)<=6.00001
						checks+=1
						if s.visibility.point_visible(0,target)!=expected:failures.append(map_id+" "+str(scout)+" -> "+str(target))
	print("VISIBILITY_GRAPH_EQUIVALENCE: ",checks," checks; failures=",failures.size())
	if not failures.is_empty():print(failures.slice(0,5))
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
