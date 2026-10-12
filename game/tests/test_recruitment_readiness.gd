extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Readiness=preload("res://scripts/recruitment_readiness.gd")
var failures: Array=[]
var checks: int=0
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func _initialize():call_deferred("run")
func run():
	for side in [0,1]:
		var s=Simulation.new(Data.new())
		s.start({"map":"map.01.01","faction":"yin","enemy":"yin","starting_gold":1000,"enemy_starting_gold":1000,"full_tech":true})
		s.ai_enabled=[false,false]
		var id: String=s.players[side].unlocked[0]
		for candidate in s.players[side].unlocked:
			if s.db.balance.units.has(candidate) and not s.db.balance.units[candidate].get("economy",false):id=candidate;break
		check(s.recruit(side,id)=="" and s.recruit(side,id)=="","Actual paid duplicate orders accepted")
		var duration: float=float(s.db.balance.units[id].get("production_seconds",2.0))
		for step in range(30):s.tick(1.0/60.0)
		var before: String=JSON.stringify(s.players[side])
		check(is_equal_approx(Readiness.queued_seconds(s,side,0),duration-0.5),"Head subtracts elapsed production")
		check(is_equal_approx(Readiness.queued_seconds(s,side,1),duration*2-0.5),"Duplicate second order includes FIFO wait")
		check(JSON.stringify(s.players[side])==before,"Readiness does not mutate economy or queue")
		var remaining: float=Readiness.queued_seconds(s,side,0)
		var elapsed: float=0
		while s.players[side].queue.size()==2 and elapsed<10:
			s.tick(1.0/60.0);elapsed+=1.0/60.0
		check(absf(elapsed-remaining)<=1.0/60.0+0.0001,"Actual production matches estimate within one tick")
		check(s.cancel_queue(side,0)=="" and Readiness.queued_seconds(s,side,0)==-1,"Cancelled empty head has no estimate")
		check(Readiness.queued_seconds(s,side,-1)==-1,"Invalid index rejected")
	for map_id in ["map.01.01","map.01.04","map.01.11"]:
		for side in [0,1]:
			var s=Simulation.new(Data.new())
			s.start({"map":map_id,"faction":"yin","enemy":"yin","full_tech":true})
			s.units.clear()
			check(Readiness.front_distance(s,side)==-1,"No own combat front yields no travel estimate")
			var unit=s.spawn("unit.yin.guard",side,float(s.bases[side].x)+(.65 if side==0 else -.65))
			s.map.advance(unit,20.0,side)
			check(absf(Readiness.front_distance(s,side)-20.0)<.0001,"Selected-road distance agrees with actual advance on "+map_id)
			var before: String=JSON.stringify([s.units,s.map.choices])
			var distance: float=Readiness.front_distance(s,side)
			check(JSON.stringify([s.units,s.map.choices])==before,"Travel calculation leaves army and route untouched")
			s.spawn("unit.yin.guard",1-side,float(unit.x))
			check(is_equal_approx(distance,Readiness.front_distance(s,side)),"Hidden enemy placement cannot change own travel estimate")
			unit.hp=0
			check(Readiness.front_distance(s,side)==-1,"Dead soldiers do not define front")
			check(Readiness.travel_notice(s,"unit.yin.worker",20).contains("采矿运输"),"Worker never pretends to reinforce combat front")
			if map_id=="map.01.04":
				s.units.clear()
				for node in s.map.nodes:
					var options: Array=s.map.outgoing[node] if side==0 else s.map.incoming[node]
					if options.size()<2:continue
					var selected: String=str(options[0])
					var other: String=str(options[1])
					s.map.choices[side][node]=selected
					var soldier=s.spawn("unit.yin.guard",side,float(s.bases[side].x))
					s.map.apply_anchor(soldier,s.map.anchor(other,float(s.map.edges[other].length)*.5))
					check(Readiness.front_distance(s,side)==-1,"Opposite branch soldier is excluded from selected route")
					s.map.choices[side][node]=other
					check(Readiness.front_distance(s,side)>0,"Changing route makes branch soldier reachable")
					break
	print("RECRUITMENT_READINESS: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
