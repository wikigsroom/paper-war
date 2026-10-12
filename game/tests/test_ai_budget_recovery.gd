extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var checks: int=0
var failures: Array=[]
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func fixture(side: int,body_count: int=2,cash: float=90,faction: String="yin"):
	var s=Simulation.new(Data.new())
	# Rush has a three-miner goal; non-rush growth is exercised by the separate
	# normal-resource workflows rather than these controlled cash fixtures.
	s.start({"map":"map.01.01","faction":faction,"enemy":faction,"starting_gold":cash,"enemy_starting_gold":cash,"ai_warmup":0,"ai_style":"rush","experimental_ai_budget_planner":true,"experimental_ai_budget_planner_side":side})
	s.ai_enabled=[false,false]
	var sign: float=1 if side==0 else -1
	# Controlled contact bodies test allocation, not normal-resource victory.
	var front: String="unit."+faction+(".blade" if faction=="mo" else ".axe")
	for i in range(body_count):s.spawn(front,side,float(s.bases[side].x)+sign*(2+i*.6))
	s.spawn("unit."+faction+".worker",side,float(s.bases[side].x))
	var p: Dictionary=s.players[side]
	p.mana=0;p["ai_budget_seeded"]=true;p["ai_budget_study"]="tech."+faction+(".unit.priest" if faction=="mo" else ".unit.hammer");p["ai_budget_bank"]=70.0
	s.visibility.refresh();s.drain_events()
	return s
func paid_order(s,side: int,id: String,initial: float,note: String):
	var p: Dictionary=s.players[side]
	var events: Array=s.drain_events().filter(func(e):return e.kind=="recruit" and e.side==side)
	check(p.queue==[id] and events.size()==1 and events[0].id==id,note+" submits one real order")
	check(is_equal_approx(float(p.gold),initial-float(s.db.balance.units[id].gold)),note+" pays the authored fee")
	check(is_equal_approx(float(p.ai_budget_bank),float(p.gold)),note+" consumes only the needed reserve")
func run():
	for side in [0,1]:
		var s=fixture(side);var p: Dictionary=s.players[side]
		AI.turn(s,side)
		paid_order(s,side,"unit.yin.spear",90,"Recover two surviving fronts "+str(side))
		check(p.ai_budget_study=="tech.yin.unit.hammer" and p.research.is_empty(),"Recovery retains the unfunded study without a free unlock "+str(side))
		check(s.request(side,"cancel_queue",{"index":0,"id":"unit.yin.spear","queue_revision":p.queue_revision}).ok and p.gold==90,"Recovery order obeys the public refund command "+str(side))
		s=fixture(side,2,59);p=s.players[side];p.ai_budget_bank=59
		AI.turn(s,side)
		paid_order(s,side,"unit.yin.axe",59,"Affordable body while second shooter is unaffordable "+str(side))
		s=fixture(side,4);p=s.players[side]
		AI.turn(s,side)
		check(p.queue.is_empty() and p.gold==24 and p.ai_budget_bank==24 and p.research.get("id","")=="tech.yin.unit.hammer" and p.ai_budget_unit=="unit.yin.hammer","Established formation pays research now and retains only actual remaining cash "+str(side))
		s=fixture(side,3);p=s.players[side]
		AI.turn(s,side)
		check(p.queue.is_empty() and p.gold==24 and p.ai_budget_bank==24 and p.research.get("id","")=="tech.yin.unit.hammer" and p.ai_budget_unit=="unit.yin.hammer","One casualty does not preempt a funded study or fabricate its later recruit fee "+str(side))
		s=fixture(side,3);p=s.players[side]
		p.ai_budget_seeded=false;p.ai_budget_study="";p.ai_budget_bank=0
		AI.turn(s,side)
		check(p.queue==["unit.yin.spear"] and p.gold==30 and not p.ai_budget_seeded,"The first opening still pays for its fourth body "+str(side))
		AI.turn(s,side)
		check(p.ai_budget_seeded and p.ai_budget_study=="tech.yin.unit.hammer" and p.queue==["unit.yin.spear"],"Only the actual four-body opening starts its investment "+str(side))
		s=fixture(side,2,156);p=s.players[side]
		p.ai_budget_study="";p["ai_budget_unit"]="unit.yin.hammer";p.ai_budget_bank=90
		check(s.request(side,"research",{"id":"tech.yin.unit.hammer"}).ok and p.gold==90,"Unfinished study was paid through the public command "+str(side))
		AI.turn(s,side)
		paid_order(s,side,"unit.yin.spear",90,"Recover during an unfinished paid study "+str(side))
		check(p.ai_budget_unit=="unit.yin.hammer" and not p.unlocked.has("unit.yin.hammer"),"Recovery preserves the pending grant and does not unlock early "+str(side))
		# A completed contact-unit study keeps its first-recruit funds once the
		# three-body formation exists; it cannot waive the real recruit fee.
		# Fixture treasury edits below isolate affordability boundaries. They
		# are not evidence of normal-resource battle outcomes.
		s=fixture(side,3,156);p=s.players[side]
		p.ai_budget_study="";p["ai_budget_unit"]="unit.yin.hammer"
		check(s.request(side,"research",{"id":"tech.yin.unit.hammer"}).ok and p.gold==90,"Replacement study pays its actual fee "+str(side))
		while s.time<6:s.tick(1.0/60.0)
		check(p.unlocked.has("unit.yin.hammer") and p.research.is_empty(),"Replacement savings wait for the real research timer "+str(side))
		s.drain_events();p.gold=94;p.ai_budget_bank=94
		AI.turn(s,side)
		check(p.queue.is_empty() and p.gold==94 and p.ai_budget_bank==94 and p.ai_budget_unit=="unit.yin.hammer","Three defended bodies preserve a completed frontline replacement one coin below its fee "+str(side))
		p.gold+=1;AI.turn(s,side)
		paid_order(s,side,"unit.yin.hammer",95,"Actual-price advanced contact replacement "+str(side))
		# A ranged support cannot replace a missing third combat body merely because
		# its study is done and its recruitment price is already affordable.
		s=fixture(side,2,161,"mo");p=s.players[side]
		p.ai_budget_study="";p["ai_budget_unit"]="unit.mo.priest"
		check(s.request(side,"research",{"id":"tech.mo.unit.priest"}).ok and p.gold==95,"Support comparison pays its actual research fee "+str(side))
		while s.time<6:s.tick(1.0/60.0)
		check(p.unlocked.has("unit.mo.priest") and p.research.is_empty(),"Support comparison completes its real timer "+str(side))
		s.drain_events();p.gold=95;p.ai_budget_bank=95
		AI.turn(s,side)
		paid_order(s,side,"unit.mo.blade",95,"A support grant still requires the third paid combat body "+str(side))
		var orders: Array=[]
		for hidden_variant in [0,1]:
			s=fixture(side);p=s.players[side]
			if hidden_variant==1:
				var hidden=s.spawn("unit.yin.hammer",1-side,float(s.bases[1-side].x));hidden.hp=1
				s.players[1-side].gold=99999;s.visibility.refresh()
				check(not s.visible_to(side,hidden),"Hidden opponent remains outside actual vision "+str(side))
			AI.turn(s,side);orders.append({"queue":p.queue.duplicate(),"gold":p.gold,"bank":p.ai_budget_bank,"study":p.ai_budget_study})
		check(orders[0]==orders[1],"Unknown opponent treasury and units cannot change formation recovery "+str(side))
	var capped=fixture(1);capped.config["ai_army_limit"]=2
	AI.turn(capped,1)
	check(capped.players[1].queue.is_empty(),"An authored two-body limit does not force a four-body recovery")
	print("AI_BUDGET_RECOVERY: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
