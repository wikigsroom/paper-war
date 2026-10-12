extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var checks: int=0
var failures: Array=[]
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func advance(s,seconds: float):
	for step in range(int(ceil(seconds*60))):s.tick(1.0/60.0);s.drain_events()
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var records: Array=[]
	for faction in db.FACTIONS:
		var ids: Array=db.all_unit_ids(faction)
		verify(ids.size()==6,faction+" has six current combat definitions")
		for id in ids:
			var s=Simulation.new(db)
			s.start({"map":"map.01.01","faction":faction,"enemy":"mo","starting_gold":5000,"full_tech":true})
			s.ai_enabled=[false,false];s.units.clear();s.buildings.clear()
			var def: Dictionary=db.balance.units[id];var before: float=s.players[0].gold
			verify(s.request(0,"recruit",{"id":id}).ok,id+" current roster recruits")
			verify(is_equal_approx(before-s.players[0].gold,float(def.gold)),id+" exact paid purchase")
			advance(s,float(def.production_seconds)-.1)
			verify(s.units.filter(func(u):return u.side==0 and u.id==id).is_empty(),id+" cannot spawn before paid production ends")
			advance(s,.15)
			var recruited: Dictionary={}
			for u in s.units:
				if u.side==0 and u.id==id:recruited=u;break
			verify(not recruited.is_empty(),id+" declared production completes")
			if recruited.is_empty():continue
			s.map.apply_anchor(recruited,s.map.project(Vector2(20,0)))
			var target=s.spawn("unit.mo.giant",1,20.5)
			s.map.apply_anchor(target,s.map.anchor(recruited.edge,float(recruited.s)+.5))
			target.hp=10000;target.max_hp=10000;target.cooldown=1000;target.special_cd=1000
			var hp: float=target.hp
			advance(s,6)
			verify(target.hp<hp,id+" actual hostile damage after native combat ticks")
			verify(is_finite(recruited.x) and is_finite(recruited.y) and recruited.hp>=0,id+" finite actor state")
			records.append({"id":id,"production":def.production_seconds,"paid":def.gold,"target_damage":hp-target.hp})
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"records":records,"scope":"60 current combat units: exact purchase cost, per-unit production completion and native hostile damage. Full tech, controlled durable target; not research balance, formation balance, campaign completion or Android evidence.","inputs":{}}
	for path in ["res://scripts/battle_sim.gd","res://scripts/unit_abilities.gd","res://data/balance-prototype.json","res://tests/test_world_combat.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var args=OS.get_cmdline_user_args();var output: String=args[args.find("--output")+1] if args.has("--output") else "user://current-world-combat.json"
	var file=FileAccess.open(output,FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
	print("CURRENT_WORLD_COMBAT: ",checks," checks; failures=",failures);quit(0 if failures.is_empty() else 1)
