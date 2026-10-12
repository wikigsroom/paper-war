extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func _initialize():call_deferred("run")
func run():
	var rows: Array=[]
	for map_id in ["map.01.01","map.01.04","map.01.11"]:
		for side in [0,1]:
			for policy in ["passive","recruit_on_sight","lightning_on_sight","formation_on_sight","early_formation","lightning_then_recruit"]:
				var s=Simulation.new(Data.new())
				s.start({"map":map_id,"faction":"yin","enemy":"yin","full_tech":true,"starting_gold":300,"enemy_starting_gold":300,"seed":271})
				s.ai_enabled=[false,false]
				var enemy: int=1-side
				var worker_ids: Array=[]
				for u in s.units:
					if u.side==side:worker_ids.append(u.uid)
				var paid: Array=[]
				for i in range(2):paid.append(s.request(enemy,"recruit",{"id":"unit.yin.spear"}))
				var row={"map":map_id,"defender_side":side,"policy":policy,"attacker_orders":paid,"first_visible_at":null,"response_at":null,"response":{},"first_worker_release_at":null,"first_worker_hit_at":null,"first_worker_lost_at":null,"last_worker_lost_at":null,"response_unit_spawn_at":null,"response_unit_attack_at":null,"workers_after_response_10s":null}
				for step in range(90*60):
					var target: Dictionary={}
					for u in s.visibility.enemies[side]:
						if u.get("building",false) or u.hp<=0 or s.db.balance.units[u.id].get("economy",false):continue
						if target.is_empty():target=u
					if not target.is_empty() and row.first_visible_at==null:row.first_visible_at=s.time
					if (not target.is_empty() or policy=="early_formation") and row.response_at==null and policy!="passive":
						var result: Dictionary
						if policy in ["formation_on_sight","early_formation"]:
							var commands: Array=[]
							for id in ["unit.yin.axe","unit.yin.axe","unit.yin.spear","unit.yin.spear"]:commands.append(s.request(side,"recruit",{"id":id}))
							result={"ok":commands.all(func(c):return c.ok),"orders":commands}
						elif policy=="recruit_on_sight":result=s.request(side,"recruit",{"id":"unit.yin.axe"})
						else:
							result=s.request(side,"cast",{"id":"spell.yin.lightning","x":target.x,"y":target.y,"target":target.uid})
							if result.ok and policy=="lightning_then_recruit":result["recruit"]=s.request(side,"recruit",{"id":"unit.yin.axe"})
						if result.ok:row.response_at=s.time;row.response=result
					s.tick(1.0/60.0)
					var workers: int=s.population(side,true)
					if workers<2 and row.first_worker_lost_at==null:row.first_worker_lost_at=s.time
					if workers==0 and row.last_worker_lost_at==null:row.last_worker_lost_at=s.time
					if row.response_at!=null and s.time>=float(row.response_at)+10 and row.workers_after_response_10s==null:row.workers_after_response_10s=workers
					for u in s.units:
						if u.side==side and u.id=="unit.yin.axe" and row.response_unit_spawn_at==null:row.response_unit_spawn_at=s.time
					for e in s.drain_events():
						if e.kind=="attack" and worker_ids.has(int(e.get("target_uid",0))) and row.first_worker_release_at==null:row.first_worker_release_at=s.time
						if e.kind=="hit" and worker_ids.has(int(e.get("uid",0))) and int(e.get("source_uid",0))>0 and row.first_worker_hit_at==null:row.first_worker_hit_at=s.time
						if e.kind=="attack" and e.side==side and e.id=="unit.yin.axe" and row.response_unit_attack_at==null:row.response_unit_attack_at=s.time
					if s.winner!=-2:break
				row["time"]=s.time;row["worker_count"]=s.population(side,true);row["worker_hp"]=0.0
				for u in s.units:
					if u.side==side and s.db.balance.units[u.id].get("economy",false):row.worker_hp+=maxf(0,u.hp)
				row["gold_delivered"]=s.stats[side].gold_delivered;row["gold"]=s.players[side].gold;row["mana"]=s.players[side].mana
				row["base_hp"]=s.bases[side].hp;row["stats"]=s.stats[side].duplicate(true)
				rows.append(row)
	var report={"scope":"36 controlled paid counterplay observations: two queued enemy spears versus initial workers; no AI, full technology explicitly supplied, 300 gold per side, normal 60Hz fog/production/economy. One response on first legal sight or explicitly preplanned early formation. Not normal opening tech affordability, human reaction, all-faction balance or original-game measurements.","records":rows,"inputs":{}}
	for path in ["res://scripts/battle_sim.gd","res://scripts/battle_visibility.gd","res://scripts/map_runtime.gd","res://scripts/unit_abilities.gd","res://scripts/manual_spell_rules.gd","res://data/balance-prototype.json","res://data/maps.json","res://tests/probe_economic_counterplay.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var file=FileAccess.open(OS.get_cmdline_user_args()[0],FileAccess.WRITE)
	if file==null:push_error("Cannot write economic counterplay report");quit(1);return
	file.store_string(JSON.stringify(report,"  "));print("ECONOMIC_COUNTERPLAY ",rows.size());quit()
