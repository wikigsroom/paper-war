extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var records: Array=[]
	for faction in db.FACTIONS:
		var shooters: Array=[]
		for id in db.all_unit_ids(faction):
			var def: Dictionary=db.balance.units[id]
			if float(def.range)>1.5 and str(def.attack).begins_with("projectile"):shooters.append(id)
		shooters.sort_custom(func(a,b):return float(db.balance.units[a].range)<float(db.balance.units[b].range))
		for i in range(shooters.size()-1):
			if float(db.balance.units[shooters[i+1]].range)-float(db.balance.units[shooters[i]].range)>.54:continue
			for side in [0,1]:
				for reverse in [false,true]:
					var s=Simulation.new(db)
					s.start({"map":"map.01.01","faction":faction if side==0 else "yin","enemy":"yin" if side==0 else faction})
					s.ai_enabled=[false,false];s.units.clear();s.buildings.clear()
					var direction: float=1 if side==0 else -1
					var target=s.spawn("unit.yin.axe",1-side,20)
					target.hp=10000
					target.max_hp=10000;target.cooldown=1000;target.special_cd=1000;target.speed_override=0
					var guard_id: String=""
					for id in db.all_unit_ids(faction):
						if float(db.balance.units[id].range)<=1.5:guard_id=id;break
					if guard_id=="":guard_id="unit.yin.axe"
					var screen=s.spawn(guard_id,side,20-direction*.7)
					s.map.apply_anchor(screen,s.map.anchor(target.edge,float(target.s)-direction*.7))
					screen.cooldown=1000;screen.special_cd=1000;screen.speed_override=0
					var order: Array=[shooters[i],shooters[i+1]]
					if reverse:order.reverse()
					var members: Array=[];var releases: Dictionary={};var hits: Dictionary={}
					for j in range(2):members.append(s.spawn(order[j],side,20-direction*(7+j*.8)))
					var illegal: bool=false;var crossed: bool=false
					for step in range(20*60):
						s.tick(1.0/60.0)
						for member in members:
							if (float(member.s)-float(screen.s))*direction>-.5:crossed=true
						for e in s.drain_events():
							if e.kind=="attack" and members.any(func(u):return int(u.uid)==int(e.uid)):
								releases[e.uid]=int(releases.get(e.uid,0))+1
								var member=s.actor(int(e.uid))
								if s.combat_distance(member,target,db.balance.units[member.id])>float(db.balance.units[member.id].range)+.01:illegal=true
							if e.kind=="hit":hits[e.get("source_uid",0)]=int(hits.get(e.get("source_uid",0),0))+1
					var rows: Array=[]
					for member in members:rows.append({"id":member.id,"releases":int(releases.get(member.uid,0)),"hits":int(hits.get(member.uid,0)),"distance":s.combat_distance(member,target,db.balance.units[member.id])})
					records.append({"faction":faction,"side":side,"reverse":reverse,"members":rows,"illegal":illegal,"crossed":crossed})
	var report={"scope":"Controlled mixed ranged pairs, real weapons and screen spacing; no AI/economy, not paid-match balance.","inputs":{},"records":records}
	for path in ["res://scripts/battle_sim.gd","res://scripts/battle_visibility.gd","res://scripts/unit_abilities.gd","res://scripts/map_runtime.gd","res://tests/probe_mixed_ranged_formation.gd","res://data/balance-prototype.json","res://data/maps.json","res://data/unit-actions.json"]:report.inputs[path]=FileAccess.get_sha256(path)
	var args=OS.get_cmdline_user_args()
	if args.has("--output"):
		var file=FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
	var blocked: int=0
	for row in records:
		if row.members.any(func(u):return u.releases==0):blocked+=1
	var checks: int=0;var failures: Array=[]
	for row in records:
		checks+=2
		if row.illegal:failures.append("release outside actual weapon range")
		if row.crossed:failures.append("mixed backline crossed melee screen")
		for member in row.members:
			checks+=2
			if member.releases<3:failures.append("mixed shooter cannot repeatedly fire: "+str(member.id))
			if member.hits==0:failures.append("mixed shooter never lands a hit: "+str(member.id))
	print("MIXED_RANGED_FORMATION: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
