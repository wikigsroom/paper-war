extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const MatchProjection=preload("res://scripts/match_projection.gd")
const ClientBattle=preload("res://scripts/client_battle.gd")
var failures: Array=[]
var checks: int=0
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func run():
	var sim=Simulation.new(Data.new())
	sim.start({"map":"map.01.01","faction":"yin","enemy":"mo","starting_gold":300})
	sim.ai_enabled=[false,false]
	var hidden: Dictionary=sim.spawn("unit.mo.giant",1,sim.bases[1].x)
	sim.visibility.refresh()
	var packet: Dictionary=MatchProjection.snapshot(sim,0)
	verify(packet.opponent.keys()==["faction"],"no opponent gold, mana, queue, research or routing")
	verify(not packet.actors.any(func(a):return a.uid==hidden.uid),"hidden enemy omitted from packet")
	verify(MatchProjection.snapshot(sim,2).is_empty(),"invalid observer rejected")
	packet.player.gold=9999
	verify(sim.players[0].gold==300,"packet mutation cannot change authority")
	var visible: Dictionary=sim.spawn("unit.mo.giant",1,sim.bases[0].x+2)
	visible["private_plan"]="sentinel-private-plan"
	sim.visibility.refresh();packet=MatchProjection.snapshot(sim,0)
	var found: Array=packet.actors.filter(func(a):return a.uid==visible.uid)
	verify(found.size()==1,"revealed enemy supplied")
	verify(found.size()==1 and not found[0].has("private_plan") and not found[0].has("path"),"visible enemy uses public whitelist")
	visible.x=sim.bases[1].x;visible.edge=sim.bases[1].edge;visible.s=sim.bases[1].s
	sim.visibility.refresh();packet=MatchProjection.snapshot(sim,0)
	verify(not packet.actors.any(func(a):return a.uid==visible.uid),"lost sight stops live tracking")
	sim.projectiles=[{"uid":900,"side":1,"x":simbasex(sim),"y":sim.bases[0].y,"style":"arrow","source":hidden.uid,"target":hidden.uid,"end_x":sim.bases[1].x,"damage":999,"ability":{"secret":true}}]
	sim.spell_areas=[{"id":"spell.mo.poison","side":1,"x":sim.bases[0].x,"y":sim.bases[0].y,"left":3,"radius":2,"status":"poison","potency":999}]
	sim.corpses=[{"uid":901,"x":sim.bases[1].x,"y":sim.bases[1].y,"left":3}]
	packet=MatchProjection.snapshot(sim,0)
	verify(packet.projectiles.size()==1 and packet.projectiles[0].source==0 and packet.projectiles[0].target==0,"visible projectile masks hidden source and target")
	verify(not packet.projectiles[0].has("end_x") and not packet.projectiles[0].has("ability") and not packet.projectiles[0].has("damage"),"projectile omits hidden destination and simulation internals")
	verify(packet.spell_areas.size()==1 and not packet.spell_areas[0].has("potency"),"visible zone supplies appearance without damage internals")
	verify(packet.corpses.is_empty(),"unseen corpses omitted")
	var mirror=ClientBattle.new(sim.db);mirror.observer=0
	mirror.start({"map":"map.01.01","faction":"yin","enemy":"mo"})
	verify(mirror.apply_snapshot(packet),"client applies authoritative projection")
	verify(not mirror.apply_snapshot(packet),"duplicate or old ticks rejected")
	var before: float=mirror.time;mirror.tick(1)
	verify(mirror.time==before,"client does not simulate locally")
	verify(not mirror.request(0,"recruit",{"id":"unit.yin.axe"}).ok,"client cannot locally recruit")
	verify(mirror.bases[1].hp==0 and mirror.players[1].keys()==["faction"],"mirror retains no hidden base HP or enemy economy")
	var stream=MatchProjection.visible_events(sim,0,[{"kind":"attack","side":0,"uid":sim.units[0].uid,"x":sim.bases[0].x,"y":sim.bases[0].y,"target_uid":hidden.uid,"target_x":sim.bases[1].x,"ranged":true,"id":"unit.yin.axe"},{"kind":"cast","side":1,"x":sim.bases[1].x,"y":sim.bases[1].y,"id":"spell.mo.poison"},{"kind":"scouted","side":0,"observer":1,"x":sim.bases[0].x,"y":sim.bases[0].y}])
	verify(stream.size()==1,"hidden cast and other observer alerts omitted")
	verify(not stream[0].has("target_uid") and not stream[0].has("target_x"),"visible attack cannot expose hidden target through effects")
	print("MATCH_PROJECTION: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
func simbasex(sim) -> float:return float(sim.bases[0].x)
