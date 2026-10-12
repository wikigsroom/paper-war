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
		var sim=Simulation.new(Data.new())
		sim.start({"map":"map.01.01","faction":"mu","enemy":"mu","ai_warmup":0})
		sim.ai_enabled=[false,false]
		sim.config["experimental_ai_sequential_deployment"]=true
		sim.config["experimental_ai_sequential_funded_start"]=true
		var p: Dictionary=sim.players[side]
		var node: Dictionary=sim.db.tech("tech.mu.unit.medic")
		var direction: float=1 if side==0 else -1
		sim.spawn("unit.mu.worker",side,sim.bases[side].x)
		var front=sim.spawn("unit.mu.guard",side,sim.bases[side].x+direction)
		p.gold=float(node.gold)+109;p.ai_research_at=0
		check(not AI.sequential_purchase_ready(sim,side,node),"Cash shortfall rejects paid start without future income")
		p.gold+=1
		check(not AI.sequential_purchase_ready(sim,side,node),"One living fighter cannot finance unsupported medic study")
		var rear=sim.spawn("unit.mu.poisoner",side,sim.bases[side].x+2*direction)
		check(AI.sequential_purchase_ready(sim,side,node),"Real cash and nearby same-route formation permit study")
		var state: String=JSON.stringify([sim.players,sim.units,sim.map.choices])
		AI.sequential_purchase_ready(sim,side,node)
		check(state==JSON.stringify([sim.players,sim.units,sim.map.choices]),"Purchase observation cannot alter resources or army")
		sim.visibility.refresh();AI.turn(sim,side)
		check(p.research.get("id","")==node.id and p.gold==110 and p.ai_unit_plan==node.grant,"Actual study payment retains first recruit cash")
		rear.hp=0
		check(not AI.sequential_purchase_ready(sim,side,node),"Dead second body is not a purchase formation")
		sim.config["experimental_ai_sequential_deployment_side"]=1-side
		check(AI.sequential_purchase_ready(sim,side,node),"Other side keeps ordinary purchase rules")
		sim.config["experimental_ai_sequential_funded_start"]=false
		check(AI.sequential_purchase_ready(sim,side,node),"Default-disabled window leaves baseline unchanged")
		check(front.hp>0,"Query creates no combat damage")
		sim.config["experimental_ai_sequential_funded_start"]=true
		sim.config.erase("experimental_ai_sequential_deployment_side")
		p.research.clear();p.ai_unit_plan="";p.ai_research=node.id;p.ai_research_at=0;p.gold=70;p.queue.clear()
		rear.hp=rear.max_hp;sim.map.advance(rear,15,side)
		sim.visibility.refresh();AI.turn(sim,side)
		check(not p.queue.is_empty() and p.gold<70,"Missing formation can pay for a real basic fighter before study savings")
		check(p.ai_research==node.id and p.research.is_empty(),"Formation recovery preserves unpaid study goal without free unlock")
	print("SEQUENTIAL_PURCHASE_WINDOW: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
