extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var checks: int=0
var failures: Array=[]
func verify(value: bool,note: String):
	checks+=1
	if not value:failures.append(note)
func total(s,side: int) -> float:
	var amount: float=0
	for key in s.stats[side].mana_income:amount+=float(s.stats[side].mana_income[key])
	return amount
func step(s,seconds: float):
	for i in range(roundi(seconds*60)):s.tick(1.0/60.0)
func run():
	var db=Data.new()
	for faction in db.FACTIONS:
		var s=Simulation.new(db);s.start({"map":"map.01.01","faction":faction,"enemy":"mo","starting_gold":1000})
		s.ai_enabled=[false,false];s.players[0].mana=0
		step(s,10)
		verify(absf(total(s,0)-s.players[0].mana)<.0001,"minted source sum "+faction)
		verify(absf(float(s.stats[0].mana_income.passive)-5)<.0001,"baseline source isolated "+faction)
		var before: float=total(s,0)
		s.players[0].mana=99;s.gain_mana(0,30,"probe")
		verify(s.players[0].mana==100 and absf(total(s,0)-before-1)<.0001,"cap discards unreceived reward "+faction)
		before=total(s,0);step(s,2)
		verify(total(s,0)==before,"capped regeneration not counted "+faction)
	var s=Simulation.new(db);s.start({"map":"map.01.01","faction":"deng","enemy":"mo","full_tech":true,"starting_gold":1000})
	s.ai_enabled=[false,false];s.players[0].mana=0
	var chosen: int=-1
	for i in range(s.side_sites(0).size()):
		if s.slot_anchor(0,i).get("types",["tower","mana"]).has("mana"):chosen=i;break
	var site: Dictionary=s.slot_anchor(0,chosen)
	var scout=s.spawn("unit.deng.mirror",0,site.x);s.map.apply_anchor(scout,site)
	verify(s.request(0,"build",{"id":"building.deng.mana","slot":chosen}).ok,"paid visible facility")
	step(s,10)
	verify(float(s.stats[0].mana_income.get("facility",0))>6,"completed facility contributes")
	var before: float=float(s.stats[0].mana_income.facility)
	s.buildings[0].disabled=3;step(s,2)
	verify(s.stats[0].mana_income.facility==before,"disabled facility contributes nothing")
	verify(absf(total(s,0)-s.players[0].mana)<.0001,"facility source accounting exact")
	print("CORE_ECONOMY_SOURCES: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
