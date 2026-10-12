extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func run():
	var db=Data.new();var reports: Array=[]
	for map_id in ["map.01.01","map.01.07","map.01.11"]:
		for scenario in ["raid_economy","facility_investment","giant_control"]:
			var s=Simulation.new(db)
			var faction: String="yuan" if scenario=="raid_economy" else "deng" if scenario=="facility_investment" else "shuang"
			var enemy: String="qi" if scenario=="raid_economy" else "jin" if scenario=="facility_investment" else "mo"
			s.start({"map":map_id,"faction":faction,"enemy":enemy,"starting_gold":300,"enemy_starting_gold":300,"full_tech":scenario=="giant_control","player_ai_style":"rush" if scenario=="raid_economy" else "economy" if scenario=="facility_investment" else "counter","ai_style":"economy" if scenario=="raid_economy" else "rush","seed":431,"difficulty":1,"ai_army_limit":20})
			if scenario=="giant_control":
				# Pay a real giant recruitment order to ensure this probe contains the named threat.
				s.request(1,"recruit",{"id":"unit.mo.giant"})
			s.ai_enabled=[true,true]
			var first_seen: Array=[-1.0,-1.0];var first_release: Array=[-1.0,-1.0]
			var max_ranged: Array=[0,0];var max_combat: Array=[0,0];var worker_losses: Array=[0,0]
			var deepest: Array=[0.0,0.0];var retreat: Array=[0.0,0.0];var successful_builds: Array=[0,0]
			for i in range(90*60):
				s.tick(1.0/60.0)
				for e in s.drain_events():
					var side: int=int(e.get("side",-1))
					if side not in [0,1]:continue
					if e.kind=="attack" and first_release[side]<0:first_release[side]=s.time
					if e.kind=="building_completed":successful_builds[side]+=1
					if e.kind=="death" and str(e.get("id","")).ends_with(".worker"):worker_losses[side]+=1
				if i%30==0:
					for side in range(2):
						var ranged: int=0;var combat: int=0;var front: float=0
						for u in s.units:
							if u.side!=side or db.balance.units[u.id].get("economy",false):continue
							combat+=1
							if float(db.balance.units[u.id].range)>1.5:ranged+=1
							var progress: float=absf(u.x-s.bases[side].x)/absf(s.bases[1].x-s.bases[0].x)
							front=maxf(front,progress)
						max_ranged[side]=maxi(max_ranged[side],ranged);max_combat[side]=maxi(max_combat[side],combat)
						deepest[side]=maxf(deepest[side],front);retreat[side]=maxf(retreat[side],deepest[side]-front)
						if first_seen[side]<0 and not s.visibility.enemies[side].is_empty():first_seen[side]=s.time
				if s.winner!=-2:break
			var record={"map":map_id,"scenario":scenario,"faction":faction,"enemy":enemy,"time":s.time,"winner":s.winner,"first_seen":first_seen,"first_attack_release":first_release,"max_ranged_count":max_ranged,"max_combat":max_combat,"worker_losses":worker_losses,"completed_buildings":successful_builds,"deepest_horizontal_progress":deepest,"largest_front_pullback":retreat,"stats":s.stats,"studied":[s.players[0].studied,s.players[1].studied],"gold":[s.players[0].gold,s.players[1].gold],"mana":[s.players[0].mana,s.players[1].mana]}
			reports.append(record);print("STRATEGY_PROBE ",map_id," ",scenario," t=",s.time," winner=",s.winner)
	var args=OS.get_cmdline_user_args();var file=FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE)
	file.store_string(JSON.stringify({"scope":"Nine paid AI-vs-AI native 60Hz probes on short/medium/long maps, formal fog. Aggregate ranged count and horizontal front pullback are diagnostic proxies, not proof of a cohesive counterattack.","records":reports},"  "));file.close();quit()
func _initialize():call_deferred("run")
