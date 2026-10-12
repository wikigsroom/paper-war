extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Geometry=preload("res://scripts/map_runtime.gd")
func run():
	var db=Data.new();var reports: Array=[]
	for map_id in ["map.01.01","map.01.07","map.01.11"]:
		for with_workers in [true,false]:
			var graph=Geometry.new(db.map_definition(map_id))
			var mine: Dictionary=graph.definition.mines.filter(func(m):return int(m.owner)==1)[0]
			var opening: Array=[]
			for i in range(3):
				var anchor: Dictionary=graph.project(Vector2(float(mine.x)-3-i*.65,graph.ground_y_at(float(mine.x)-3-i*.65)))
				anchor.merge({"side":0,"id":"unit.yin.axe"});opening.append(anchor)
			var s=Simulation.new(db)
			s.start({"map":map_id,"faction":"yin","enemy":"yin","starting_gold":500,"enemy_starting_gold":400,"opening_forces":opening})
			s.ai_enabled=[false,false]
			if not with_workers:s.units=s.units.filter(func(u):return not (u.side==1 and u.id.ends_with(".worker")))
			var raid_uids: Array=[]
			for u in s.units:
				if u.side==0 and u.id=="unit.yin.axe":raid_uids.append(u.uid)
			for i in range(4):s.request(1,"recruit",{"id":"unit.yin.spear"})
			for i in range(2):s.request(0,"recruit",{"id":"unit.yin.axe"})
			var max_group: int=0;var repulse_at: float=-1;var counter_at: float=-1;var worker_losses: int=0
			var first_worker_hit: float=-1;var first_defender_attack: float=-1;var first_defender_unit_hit: float=-1
			for i in range(60*60):
				s.tick(1.0/60.0)
				for e in s.drain_events():
					if e.kind=="hit":
						var victim: Dictionary=s.actor(int(e.get("uid",0)))
						if not victim.is_empty() and victim.side==1:
							if victim.id.ends_with(".worker") and first_worker_hit<0:first_worker_hit=s.time
							elif victim.id=="unit.yin.spear" and first_defender_unit_hit<0:first_defender_unit_hit=s.time
					if e.kind=="attack" and int(e.get("side",-1))==1 and first_defender_attack<0:first_defender_attack=s.time
					if e.kind=="death" and int(e.get("side",-1))==1 and str(e.get("id","")).ends_with(".worker"):worker_losses+=1
				var ranged: Array=s.units.filter(func(u):return u.side==1 and u.id=="unit.yin.spear" and u.hp>0)
				for u in ranged:
					var group: int=0
					for other in ranged:
						if s.physical_point(u).distance_to(s.physical_point(other))<=6:group+=1
					max_group=maxi(max_group,group)
					if repulse_at>=0 and u.x<float(mine.x)-4 and counter_at<0:counter_at=s.time
				if repulse_at<0 and raid_uids.all(func(uid):return s.actor(uid).is_empty()):repulse_at=s.time
				if s.winner!=-2:break
			reports.append({"map":map_id,"with_defender_workers":with_workers,"first_defender_unit_hit":first_defender_unit_hit,"paid_raid_cost":135,"paid_defender_cost":240,"paid_attacker_reinforcement_cost":90,"first_worker_hit":first_worker_hit,"first_defender_attack":first_defender_attack,"worker_losses":worker_losses,"max_ranged_group_within_6":max_group,"raid_repulsed_at":repulse_at,"counterpush_past_mine_at":counter_at,"defender_survivors":s.units.filter(func(u):return u.side==1 and u.id=="unit.yin.spear").size(),"stats":s.stats})
	var args=OS.get_cmdline_user_args();var file=FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE)
	file.store_string(JSON.stringify({"scope":"Paid authored three-unit raid near defender mine, four ranged defenders bought through real production queue, two attacker reinforcements bought at own base. AI disabled to isolate worker delay/group/counterpush; without-worker cases are a controlled subtraction to isolate economic-body delay, not normal gameplay or a matched-faction balance proof.","records":reports},"  "));file.close()
	print("WORKER_COUNTERPUSH ",JSON.stringify(reports));quit()
func _initialize():call_deferred("run")
