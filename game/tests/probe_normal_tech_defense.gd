extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var rows: Array=[]
	for map_id in ["map.01.01","map.01.04","map.01.11"]:
		for side in [0,1]:
			for faction in ["yin","bai"]:
				var policies: Array=["recruit_only","spell_and_recruit"]
				if faction=="bai":policies.append_array(["early_research_spell_and_recruit","reactive_research_spell_and_recruit"])
				for policy in policies:
					var s=Simulation.new(db)
					var options={"map":map_id,"faction":faction if side==0 else "yin","enemy":"yin" if side==0 else faction,"full_tech":false,"starting_gold":300,"enemy_starting_gold":300,"seed":271}
					s.start(options);s.ai_enabled=[false,false];s.drain_events()
					var spell: String="spell."+faction+(".lightning" if faction=="yin" else ".fire")
					var front: String="unit."+faction+(".axe" if faction=="yin" else ".mirror")
					var row={"map":map_id,"side":side,"faction":faction,"policy":policy,"spell":spell,"front":front,"options":options,"first_visible_at":null,"front_order_at":null,"front_result":{},"research_order_at":null,"research_result":{},"research_done_at":null,"cast_at":null,"cast_result":{},"first_cast_rejection":null,"first_worker_release_at":null,"first_worker_hit_at":null,"first_worker_lost_at":null,"last_worker_lost_at":null,"initial_unlocked":s.players[side].unlocked.duplicate(),"attacker_orders":[]}
					for i in range(2):row.attacker_orders.append(s.request(1-side,"recruit",{"id":"unit.yin.spear"}))
					if policy=="early_research_spell_and_recruit":
						row.research_result=s.request(side,"research",{"id":"tech.bai.unit.scribe"});row.research_order_at=s.time
					var workers: Array=[]
					for u in s.units:
						if u.side==side:workers.append(u.uid)
					for step in range(90*60):
						var target: Dictionary={}
						for u in s.visibility.enemies[side]:
							if u.get("building",false) or u.hp<=0 or db.balance.units[u.id].get("economy",false):continue
							if target.is_empty():target=u
						if not target.is_empty():
							if row.first_visible_at==null:row.first_visible_at=s.time
							if policy=="reactive_research_spell_and_recruit" and row.research_order_at==null:
								row.research_result=s.request(side,"research",{"id":"tech.bai.unit.scribe"});row.research_order_at=s.time
							if row.front_order_at==null:
								row.front_result=s.request(side,"recruit",{"id":front})
								if row.front_result.ok:row.front_order_at=s.time
							if policy!="recruit_only" and row.cast_at==null:
								var result: Dictionary=s.request(side,"cast",{"id":spell,"x":target.x,"y":target.y,"target":target.uid})
								if result.ok:row.cast_at=s.time;row.cast_result=result
								elif row.first_cast_rejection==null:row.first_cast_rejection={"at":s.time,"error":result.error,"mana":s.players[side].mana}
						s.tick(1.0/60.0)
						if s.population(side,true)<2 and row.first_worker_lost_at==null:row.first_worker_lost_at=s.time
						if s.population(side,true)==0 and row.last_worker_lost_at==null:row.last_worker_lost_at=s.time
						for e in s.drain_events():
							if e.kind=="research_done" and e.side==side:row.research_done_at=s.time
							if e.kind=="attack" and workers.has(int(e.get("target_uid",0))) and row.first_worker_release_at==null:row.first_worker_release_at=s.time
							if e.kind=="hit" and workers.has(int(e.get("uid",0))) and row.first_worker_hit_at==null:row.first_worker_hit_at=s.time
						if s.winner!=-2:break
					row["time"]=s.time;row["worker_count"]=s.population(side,true);row["gold"]=s.players[side].gold;row["mana"]=s.players[side].mana;row["studied"]=s.players[side].studied.duplicate();row["stats"]=s.stats[side].duplicate(true)
					rows.append(row)
					print("NORMAL_TECH_DEFENSE ",map_id," side=",side," ",faction," ",policy," workers=",row.worker_count," cast=",row.cast_at)
	var report={"scope":"36 controlled normal-technology paid defense observations, 300 gold per side, two normally queued enemy spears, initial workers, no AI, formal 60Hz fog. One front recruited at first legal sight, optional single spell when legal/affordable, optional actual scribe research early or on sight. No free unlocks, mana grants or production skip. Not human reaction, all-faction/all-map balance or original-game measurement.","records":rows,"inputs":{}}
	for path in ["res://scripts/battle_sim.gd","res://scripts/battle_visibility.gd","res://scripts/map_runtime.gd","res://scripts/unit_abilities.gd","res://scripts/manual_spell_rules.gd","res://data/balance-prototype.json","res://data/maps.json","res://data/technology.json","res://tests/probe_normal_tech_defense.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var file=FileAccess.open(OS.get_cmdline_user_args()[0],FileAccess.WRITE)
	if file==null:push_error("Cannot write normal-tech defense report");quit(1);return
	file.store_string(JSON.stringify(report,"  "));quit()
