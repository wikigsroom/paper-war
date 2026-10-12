extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var checks: int=0
var failures: Array=[]
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func _initialize():call_deferred("run")
func run():
	for side in [0,1]:
		var s=Simulation.new(Data.new())
		s.start({"map":"map.01.01","faction":"mu","enemy":"mu","starting_gold":300,"enemy_starting_gold":300,"ai_warmup":0})
		s.ai_enabled=[false,false]
		s.config["experimental_ai_staged_deployment"]=true;s.config["experimental_ai_staged_deployment_side"]=side
		var p: Dictionary=s.players[side]
		var node: Dictionary=s.db.tech("tech.mu.unit.medic")
		var minimum: float=float(node.gold)+float(s.db.balance.units[node.grant].gold)*.25
		p.gold=minimum-1
		check(not AI.staged_research_affordable(s,side,node),"Insufficient research plus partial reserve refused")
		p.gold=minimum
		check(AI.staged_research_affordable(s,side,node) and not AI.funded_research_affordable(s,side,node),"Partial reserve admits staged investment without full future gold")
		p.gold=300
		check(s.request(side,"recruit",{"id":"unit.mu.guard"}).ok and s.request(side,"recruit",{"id":"unit.mu.poisoner"}).ok,"Opening pair pays real 132 gold")
		AI.turn(s,side)
		check(p.research.get("id","")==node.id and p.queue.size()==2,"Research starts after pair before extra worker or third soldier")
		check(p.gold==91 and p.get("ai_stage_opened",false),"Research payment leaves actual 91 gold, not promised 110")
		var spent: float=0
		for event in s.drain_events():
			if event.kind=="recruit" and event.side==side:spent+=float(s.db.balance.units[event.id].gold)
			if event.kind=="research_start" and event.side==side:spent+=float(s.db.tech(event.id).gold)
		s.ai_enabled[side]=true
		var paid_medic: bool=false;var live_medic: bool=false;var paid_at: float=-1
		for i in range(24*60):
			s.tick(1.0/60.0)
			for event in s.drain_events():
				if event.kind=="recruit" and event.side==side:
					spent+=float(s.db.balance.units[event.id].gold)
					if event.id==node.grant:paid_medic=true;paid_at=event.time
				if event.kind=="research_start" and event.side==side:spent+=float(s.db.tech(event.id).gold)
			for u in s.units:
				if u.side==side and u.id==node.grant and u.hp>0:live_medic=true
		check(paid_medic and paid_at>=float(node.seconds),"Medic payment follows actual unlock and income")
		check(live_medic,"Staged plan actually produces support")
		check(is_equal_approx(p.gold,300+float(s.stats[side].gold_delivered)-spent),"Gold ledger contains no free deployment or forecast income")
		check(p.get("ai_unit_plan","")=="","Fulfilled plan releases staged reserve")
	print("STAGED_DEPLOYMENT: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
