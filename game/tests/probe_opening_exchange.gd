extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var records: Array=[];var args=OS.get_cmdline_user_args()
	for id in db.balance.units:
		var def: Dictionary=db.balance.units[id]
		if def.get("economy",false) or not def.get("manual_recruit",false) or int(def.get("tier",-1))!=0:continue
		for opponent in ["unit.yin.axe","unit.mo.blade"]:
			for side in [0,1]:
				var faction: String=str(def.faction);var enemy_faction: String=str(db.balance.units[opponent].faction)
				var s=Simulation.new(db)
				s.start({"map":"map.01.01","faction":faction if side==0 else enemy_faction,"enemy":enemy_faction if side==0 else faction,"full_tech":true,"starting_gold":300,"enemy_starting_gold":300})
				s.ai_enabled=[false,false];s.units.clear();s.buildings.clear()
				var counts: Array=[];var costs: Array=[]
				for team in [0,1]:
					var actor: String=id if team==side else opponent
					var count: int=int(floor(300.0/float(db.balance.units[actor].gold)))
					counts.append(count);costs.append(count*float(db.balance.units[actor].gold))
					s.players[team].gold-=float(costs[team])
					var center: float=(float(s.bases[0].x)+float(s.bases[1].x))*.5
					for i in range(count):s.spawn(actor,team,center-5-i*.8 if team==0 else center+5+i*.8)
				var attacks: Array=[0,0];var actual_damage: Array=[0.0,0.0]
				for step in range(60*60):
					s.tick(1.0/60.0)
					for e in s.drain_events():
						if e.kind=="attack":attacks[int(e.side)]+=1
						if e.kind=="hit" and int(e.get("source_uid",0))>0:actual_damage[1-int(e.side)]+=float(e.amount)
					if s.population(0,false)==0 or s.population(1,false)==0:break
				var survivors: Array=[s.population(0,false),s.population(1,false)]
				var hp: Array=[0.0,0.0]
				for u in s.units:
					if u.hp>0:hp[int(u.side)]+=float(u.hp)
				records.append({"id":id,"opponent":opponent,"candidate_side":side,"time":s.time,"counts":counts,"purchase_costs":costs,"survivors":survivors,"hp":hp,"attack_releases":attacks,"actual_hit_damage":actual_damage,"healed":[s.stats[0].healed,s.stats[1].healed],"formation_center":(float(s.bases[0].x)+float(s.bases[1].x))*.5})
	var report={"scope":"Controlled homogeneous starting-tier purchase-budget exchange; each side buys as many units as 300 gold permits, remainder retained. Formal fog, no AI, workers, buildings, spells, research or production timing. Not normal opening balance or reference-game measurement.","records":records,"inputs":{}}
	for source in ["res://scripts/battle_sim.gd","res://scripts/unit_abilities.gd","res://scripts/battle_visibility.gd","res://scripts/map_runtime.gd","res://data/balance-prototype.json","res://data/maps.json","res://tests/probe_opening_exchange.gd"]:report.inputs[source]=FileAccess.get_sha256(source)
	var file=FileAccess.open(args[0],FileAccess.WRITE)
	if file==null:push_error("Cannot write opening exchange report");quit(1);return
	file.store_string(JSON.stringify(report,"  "));file.close()
	print("OPENING_EXCHANGE ",records.size());quit()
