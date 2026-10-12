extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var checks: int=0
var failures: Array=[]
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func make(db,side: int):
	var s=Simulation.new(db)
	s.start({"map":"map.01.04","faction":"mu" if side==0 else "mo","enemy":"mo" if side==0 else "mu","starting_gold":0,"enemy_starting_gold":0,"ai_warmup":0})
	s.ai_enabled=[false,false];s.time=20
	s.players[side].mana=0
	return s
func run():
	var db=Data.new()
	for side in [0,1]:
		var s=make(db,side)
		var ally=s.spawn("unit.mu.guard",side,22)
		var enemy=s.spawn("unit.mo.blade",1-side,13 if side==0 else 31)
		var scout=s.spawn("unit.mu.worker",side,enemy.x)
		s.set_status(scout,"bind",10,0);s.visibility.refresh()
		verify(s.visible_to(side,enemy) and AI.dist(enemy,s.bases[side])>9,"legal sighting outside old nine-unit defense threshold "+str(side))
		verify(AI.uncovered_approach(s,side,[enemy],[ally]),"distant offensive front does not screen a bypassed approach "+str(side))
		s.players[side].gold=80;s.players[side].ai_research="tech.mu.unit.medic"
		AI.turn(s,side)
		verify(s.players[side].ai_research=="" and s.players[side].research.is_empty(),"visible uncovered approach releases research savings "+str(side))
		verify(s.buildings.size()==1 and s.buildings[0].side==side and s.buildings[0].id=="building.mu.tower" and s.players[side].gold==0,"emergency tower uses actual 80-gold cost without artificial 120 threshold "+str(side))
		verify(s.buildings[0].state=="constructing" and s.buildings[0].construction==5,"defensive tower still pays its full construction wait "+str(side))
	var s=make(db,0)
	var ally=s.spawn("unit.mu.guard",0,22)
	var enemy=s.spawn("unit.mo.blade",1,13)
	s.visibility.refresh()
	verify(not s.visible_to(0,enemy),"bypassed actor without scout is actually hidden")
	s.players[0].gold=50;s.players[0].ai_research="tech.mu.unit.medic";AI.turn(s,0)
	verify(s.players[0].ai_research=="tech.mu.unit.medic" and s.buildings.is_empty(),"hidden bypass does not release research or grant defensive intel")
	s=make(db,0);ally=s.spawn("unit.mu.guard",0,10);enemy=s.spawn("unit.mo.blade",1,13)
	s.visibility.refresh()
	verify(not AI.uncovered_approach(s,0,[enemy],[ally]),"homeward screen can intercept approaching enemy")
	s=make(db,1);ally=s.spawn("unit.mu.poisoner",1,26.1);enemy=s.spawn("unit.mo.blade",0,30)
	s.map.apply_anchor(enemy,s.map.anchor("bridge",float(s.map.edges.bridge.length)-.01))
	verify(AI.uncovered_approach(s,1,[enemy],[ally]),"ranged fire from behind cannot be mistaken for a lasting screen at merge")
	s=make(db,0);ally=s.spawn("unit.mu.guard",0,22);enemy=s.spawn("unit.mo.blade",1,39)
	verify(not AI.uncovered_approach(s,0,[enemy],[ally]),"distant enemy does not force premature defense even when supplied as known")
	s=make(db,0);ally=s.spawn("unit.mu.guard",0,22);enemy=s.spawn("unit.mo.blade",1,13)
	var scout=s.spawn("unit.mu.worker",0,13);s.set_status(scout,"bind",10,0);s.visibility.refresh()
	s.players[0].gold=79;s.players[0].ai_research="tech.mu.unit.medic";AI.turn(s,0)
	verify(s.buildings.is_empty() and s.players[0].gold>=0,"79 gold cannot buy an 80-gold tower")
	verify(s.players[0].research.is_empty() and not s.players[0].queue.is_empty(),"insufficient tower funds may pay an affordable defensive fighter")
	s=make(db,0);s.time=8;s.players[0].gold=80
	s.spawn("unit.mu.guard",0,10);s.spawn("unit.mu.poisoner",0,9);s.visibility.refresh()
	AI.turn(s,0)
	verify(s.buildings.is_empty() and s.players[0].gold==45,"safe opening pays 35 for third worker before optional watchpost")
	verify(s.players[0].queue==["unit.mu.worker"] and s.population(0,true,false)==2 and s.population(0,true,true)==3,"paid third-worker queue is not an instant spawned miner")
	s=make(db,0);s.time=3;s.players[0].gold=80;s.players[0].queue=["unit.mu.guard","unit.mu.poisoner"]
	s.visibility.refresh();AI.turn(s,0)
	verify(s.buildings.is_empty() and s.players[0].gold==80 and s.players[0].queue.size()==2,"queued opening can reserve an unseen watchpost but cannot build it through fog")
	verify(s.players[0].ai_build_reserve==0,"optional scout reserve waits for the intended opening crew")
	s=make(db,0);s.time=8;s.players[0].gold=80
	# Explicit crew/position fixture: not a normal paid match or free-income proof.
	s.spawn("unit.mu.guard",0,10);s.spawn("unit.mu.poisoner",0,9);s.spawn("unit.mu.worker",0,4);s.visibility.refresh()
	AI.turn(s,0)
	verify(s.buildings.size()==1 and s.buildings[0].id=="building.mu.tower" and s.players[0].gold==0,"satisfied three-worker crew can pay the normal 80-gold watchpost")
	verify(s.players[0].queue.is_empty(),"watchpost payment does not create another miner")
	s=make(db,0);s.config.player_ai_style="rush";s.time=8;s.players[0].gold=80
	s.spawn("unit.mu.guard",0,10);s.spawn("unit.mu.poisoner",0,9);s.visibility.refresh();AI.turn(s,0)
	verify(s.buildings.is_empty() and s.players[0].ai_build_reserve==0,"rush style retains army investment instead of mandatory watchpost")
	s=make(db,0);s.players[0].unlocked.erase("building.mu.tower")
	verify(AI.watchpost_slot(s,0)==-1,"locked tower cannot reserve a scout budget")
	s=make(db,0);s.players[0].gold=80;s.spawn("unit.mu.guard",0,10);s.visibility.refresh()
	s.request(0,"build",{"id":"building.mu.tower","slot":0})
	verify(AI.watchpost_slot(s,0)==-1,"existing or constructing tower prevents another opening reservation")
	print("AI_ROUTE_DEFENSE: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
