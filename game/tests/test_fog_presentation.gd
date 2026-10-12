extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Client=preload("res://scripts/client_battle.gd")
const MatchProjection=preload("res://scripts/match_projection.gd")
const Fog=preload("res://scripts/theatre_fog.gd")
var checks: int=0
var failures: Array=[]
func verify(value: bool,note: String):
	checks+=1
	if not value:failures.append(note)
func _initialize():call_deferred("run")
func run():
	var db=Data.new()
	for side in range(2):
		var sim=Simulation.new(db);sim.start({"map":"map.01.04","faction":"yin","enemy":"yin","full_tech":true})
		sim.units.clear()
		for base in sim.bases:base.hp=0
		var scout=sim.spawn("unit.yin.axe",side,22)
		sim.map.apply_anchor(scout,sim.map.anchor("ground.2",8))
		var hidden=sim.spawn("unit.mo.giant",1-side,22)
		sim.map.apply_anchor(hidden,sim.map.anchor("bridge",sim.map.edges.bridge.length*.5))
		sim.visibility.refresh()
		var local: Dictionary=sim.map.anchor("ground.2",8)
		var remote: Dictionary=sim.physical_anchor(hidden)
		verify(sim.visibility.point_visible(side,local),"own scout sight")
		verify(not sim.visibility.point_visible(side,remote),"hidden parallel road")
		verify(sim.visibility.point_explored(side,local) and not sim.visibility.point_explored(side,remote),"separate explored roads")
		verify(is_zero_approx(Fog.opacity(sim.visibility,side,local,sim.map.edges[local.edge].length)),"clear interior has no wash")
		verify(is_equal_approx(Fog.opacity(sim.visibility,side,remote,sim.map.edges[remote.edge].length),Fog.UNKNOWN_ALPHA),"unexplored upper road is dense fog")
		var value: float=sim.players[side].mana
		verify(not sim.request(side,"cast",{"id":"spell.yin.lightning","target":hidden.uid,"x":hidden.x,"y":hidden.y}).ok,"unrevealed spell rejected")
		verify(sim.players[side].mana==value,"unrevealed spell does not charge")
		var renderer=Fog.new();renderer.prepare(sim.map)
		verify(not renderer.columns.is_empty(),"world columns constructed")
		verify(is_zero_approx(float(renderer.columns[0].lo)) and is_equal_approx(float(renderer.columns[-1].hi),sim.map.length),"fog covers paper margins beyond road endpoints")
		var profile: Array=[]
		for column in renderer.columns:
			for road in column.roads:
				for end in ["left","right"]:
					var anchor: Dictionary=road[end]
					var projected: Vector2=sim.map.point(anchor.edge,float(anchor.s))
					verify(projected.distance_to(Vector2(anchor.x,anchor.y))<.001,"fog geometry follows actual road")
					profile.append(Fog.opacity(sim.visibility,side,anchor,sim.map.edges[anchor.edge].length))
		var mirror=Client.new(db);mirror.start(sim.config);mirror.observer=side
		verify(mirror.apply_snapshot(MatchProjection.snapshot(sim,side)),"projected client accepts state")
		var copy: Array=[]
		for column in renderer.columns:
			for road in column.roads:
				for end in ["left","right"]:
					var anchor: Dictionary=road[end]
					copy.append(Fog.opacity(mirror.visibility,side,anchor,mirror.map.edges[anchor.edge].length))
		verify(profile==copy,"LAN and authority produce identical fog")
		scout.hp=0;sim.visibility.refresh()
		verify(not sim.visibility.point_visible(side,local) and sim.visibility.point_explored(side,local),"lost observer retracts sight but preserves terrain memory")
		verify(is_equal_approx(Fog.opacity(sim.visibility,side,local,sim.map.edges[local.edge].length),Fog.REMEMBERED_ALPHA),"retracted fog is distinct from unexplored fog")
		verify(not sim.visible_to(side,hidden),"history cannot track hidden moving actors")
		var a: Dictionary={"edge":"lane","s":5.5};var sight=sim.visibility
		sight.current[side]={"lane":[Vector2(2,6)]};sight.explored[side]={"lane":[Vector2(2,6)]}
		var inside: float=Fog.opacity(sight,side,a,10)
		a.s=6.0;var boundary: float=Fog.opacity(sight,side,a,10)
		a.s=6.05;var outside: float=Fog.opacity(sight,side,a,10)
		verify(inside>0 and inside<boundary and is_equal_approx(boundary,outside),"soft edge does not clear unobserved territory")
		var roads: Array=[{"left":{"y":-4},"right":{"y":-4}},{"left":{"y":0},"right":{"y":0}}]
		verify(is_equal_approx(Fog.vertical_alpha(roads,[.9,0.0],-4,"left"),.9),"unseen bridge deck remains obscured")
		verify(is_zero_approx(Fog.vertical_alpha(roads,[.9,0.0],0,"left")),"visible lower deck is clear")
		var previous: float=1
		for i in range(25):
			var alpha: float=Fog.vertical_alpha(roads,[.9,0.0],-2.7+i*.06,"left")
			verify(alpha<=previous+.00001 and alpha>=0 and alpha<=.9,"vertical separation blends without sharp strip")
			previous=alpha
	print("FOG_PRESENTATION: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
