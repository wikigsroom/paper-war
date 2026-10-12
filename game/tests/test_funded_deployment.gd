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
		s.start({"map":"map.01.01","faction":"mu","enemy":"mu","ai_warmup":0})
		s.ai_enabled=[false,false];s.config["experimental_ai_funded_deployment"]=true
		var p: Dictionary=s.players[side]
		var node: Dictionary=s.db.tech("tech.mu.unit.medic")
		var total: float=float(node.gold)+float(s.db.balance.units[node.grant].gold)
		p.gold=total-1
		check(not AI.funded_research_affordable(s,side,node),"Research alone cannot spend first-deployment budget")
		p.gold=total
		check(AI.funded_research_affordable(s,side,node),"Exact unlock plus recruit budget admitted")
		var sign: float=1 if side==0 else -1
		s.spawn("unit.mu.worker",side,s.bases[side].x)
		var front=s.spawn("unit.mu.guard",side,s.bases[side].x+2*sign)
		s.spawn("unit.mu.guard",side,s.bases[side].x+3*sign)
		p.ai_research_at=0;s.visibility.refresh();AI.turn(s,side)
		check(p.research.get("id","")==node.id and p.get("ai_unit_plan","")==node.grant,"Actual paid research creates first-unit plan")
		check(p.gold==float(s.db.balance.units[node.grant].gold) and p.queue.is_empty(),"Research leaves deployment cost intact")
		for i in range(int(ceil(float(node.seconds)*60))+1):s.tick(1.0/60.0)
		check(p.unlocked.has(node.grant),"Unlock requires actual research time")
		var before: float=p.gold
		AI.turn(s,side)
		check(p.queue==[node.grant] and is_equal_approx(p.gold,before-float(s.db.balance.units[node.grant].gold)),"Completed plan makes exact paid first recruit")
		AI.turn(s,side)
		check(p.get("ai_unit_plan","")=="","Queued deployment releases reservation")
		var produced: bool=false
		for i in range(300):
			s.tick(1.0/60.0)
			for u in s.units:
				if u.side==side and u.id==node.grant:produced=true
		check(produced,"Planned support actually exits production")
		p.ai_unit_plan=node.grant;p.ai_unit_plan_until=s.time-1
		AI.turn(s,side)
		check(p.ai_unit_plan=="","Expired plan cannot reserve forever")
		for u in s.units:
			if u.side==side and not s.db.balance.units[u.id].get("economy",false):u.hp=0
		p.ai_unit_plan=node.grant;p.ai_unit_plan_until=s.time+30;p.gold=110
		s.spawn("unit.mu.guard",1-side,s.bases[side].x+.65*sign)
		s.visibility.refresh();AI.turn(s,side)
		check(p.queue.has("unit.mu.guard") and not p.queue.has(node.grant),"Visible outlet emergency may spend reserved gold on actual screen")
		s.start({"map":"map.01.01","faction":"mu","enemy":"mu","ai_warmup":0})
		s.ai_enabled=[false,false];s.config["experimental_ai_funded_deployment"]=true;s.config["experimental_ai_funded_deployment_side"]=1-side
		p=s.players[side];p.gold=total;p.ai_research_at=0
		s.spawn("unit.mu.worker",side,s.bases[side].x)
		s.spawn("unit.mu.guard",side,s.bases[side].x+2*sign);s.spawn("unit.mu.guard",side,s.bases[side].x+3*sign)
		s.visibility.refresh();AI.turn(s,side)
		check(p.get("ai_unit_plan","")=="","Side-scoped pilot cannot change opponent investment plan")
	print("FUNDED_DEPLOYMENT: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
