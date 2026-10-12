extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var checks: int=0
var failures: Array=[]
var cases: Array=[]
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func fixture(side: int,faction: String="yin"):
	var s=Simulation.new(Data.new())
	# Controlled reserve boundaries use the authored rush profile (three
	# workers); paid_workflows below exercises normal counter-profile growth.
	s.start({"map":"map.01.01","faction":faction,"enemy":faction,"starting_gold":300,"enemy_starting_gold":300,"ai_warmup":0,"ai_style":"rush","seed":137,"experimental_ai_budget_planner":true,"experimental_ai_budget_planner_side":side})
	s.ai_enabled=[false,false];s.players[side].mana=0;s.drain_events()
	return s
func boundaries():
	for side in [0,1]:
		var s=fixture(side);var p: Dictionary=s.players[side]
		# Actual transport creates this income. Two real paid orders fill the
		# queue, while the temporary crew/army counts remain below the opening.
		while float(s.stats[side].gold_delivered)<8:s.tick(1.0/60.0)
		s.request(side,"recruit",{"id":"unit.yin.axe"});s.request(side,"recruit",{"id":"unit.yin.spear"})
		var delivered: float=float(s.stats[side].gold_delivered);var before: float=float(p.gold)
		p["ai_budget_seeded"]=true;p["ai_budget_study"]="tech.yin.unit.hammer";p["ai_budget_bank"]=30.0;p["ai_budget_delivered"]=0.0
		AI.turn(s,side)
		check(is_equal_approx(float(p.ai_budget_bank),30+delivered*.35),"Existing study retains actual income through temporary opening-count loss "+str(side))
		check(p.gold==before and p.research.is_empty(),"Savings do not create cash or buy an unfunded study "+str(side))
		var bank: float=float(p.ai_budget_bank);AI.turn(s,side)
		check(is_equal_approx(float(p.ai_budget_bank),bank),"An unchanged delivered counter is never credited twice "+str(side))
		# Controlled contact fixtures exercise actual commands; fixture cash and
		# prepositioned units are not reported as normal-resource battle results.
		s=fixture(side);p=s.players[side];p.gold=100
		var sign: float=1 if side==0 else -1
		for id in ["unit.yin.axe","unit.yin.spear","unit.yin.spear"]:s.spawn(id,side,float(s.bases[side].x)+sign)
		s.spawn("unit.yin.axe",1-side,float(s.bases[side].x)+sign*.65);s.visibility.refresh()
		p["ai_budget_seeded"]=true;p["ai_budget_study"]="tech.yin.unit.hammer";p["ai_budget_bank"]=40.0
		AI.turn(s,side)
		check(p.queue==["unit.yin.axe"] and p.gold==55,"Emergency reinforcement pays its actual frontline fee "+str(side))
		check(is_equal_approx(float(p.ai_budget_bank),40) and p.ai_budget_study=="tech.yin.unit.hammer","Covered emergency expense does not erase the entire existing study "+str(side))
		s=fixture(side);p=s.players[side];p.gold=60
		s.spawn("unit.yin.axe",1-side,float(s.bases[side].x)+sign*.65);s.visibility.refresh()
		p["ai_budget_seeded"]=true;p["ai_budget_study"]="tech.yin.unit.hammer";p["ai_budget_bank"]=40.0
		AI.turn(s,side)
		check(p.queue==["unit.yin.axe"] and p.gold==15,"An urgent frontline may spend reserved cash before recruiting another worker "+str(side))
		check(is_equal_approx(float(p.ai_budget_bank),15) and p.ai_budget_study=="tech.yin.unit.hammer","Emergency release consumes only real cash and preserves the remaining study balance "+str(side))
		s=fixture(side);p=s.players[side]
		var study: Dictionary=s.db.tech("tech.yin.unit.hammer")
		var research_fee: float=float(study.gold)
		for i in range(6):s.spawn("unit.yin.axe",side,float(s.bases[side].x)+sign)
		s.spawn("unit.yin.worker",side,float(s.bases[side].x));s.visibility.refresh()
		# Research and the first recruit are separate paid commands. A defended
		# formation can research without already holding the later recruit fee.
		p.gold=research_fee-1;p["ai_budget_seeded"]=true;p["ai_budget_study"]=study.id;p["ai_budget_bank"]=research_fee-1
		AI.turn(s,side)
		check(p.research.is_empty() and p.gold==research_fee-1,"One missing research coin cannot be borrowed from a future mining delivery "+str(side))
		p.gold+=1;p.ai_budget_bank+=1;AI.turn(s,side)
		check(p.research.get("id","")==study.id and p.gold==0 and p.ai_budget_unit==study.grant and p.ai_budget_bank==0 and not p.unlocked.has(study.grant) and p.queue.is_empty(),"Actual research fee starts its own timer without a free unlock or prepaid recruit "+str(side))
		for offset in [10.0,3.0,.65]:
			s=fixture(side,"jin");p=s.players[side];p.gold=90
			for i in range(2):s.spawn("unit.jin.archer",side,float(s.bases[side].x)+sign*6)
			var enemy=s.spawn("unit.jin.berserker",1-side,float(s.bases[side].x)+sign*offset);s.visibility.refresh()
			check(s.visible_to(side,enemy),"Frontline purchase uses an actually visible approaching enemy "+str(side)+" / "+str(offset))
			AI.turn(s,side)
			if offset==3:
				check(p.queue==["unit.jin.archer"] and p.gold==30,"Immediate uncamped miner danger retains an affordable ranged fallback "+str(side))
			else:
				check(p.queue.is_empty() and p.gold==90,"Expensive missing frontline is not perpetually preempted by cheap archers "+str(side)+" / "+str(offset))
			if offset==10:
				p.gold+=35;AI.turn(s,side)
				check(p.queue==["unit.jin.berserker"] and p.gold==0,"Saved frontline funds buy the real expensive recruit as soon as affordable "+str(side))
		# Opponent treasury, research and unseen troop identities may not steer
		# the player's reserve, study, build or recruitment commands.
		var variants: Array=[]
		for variant in [0,1]:
			s=fixture(side);p=s.players[side];p.gold=200
			for id in ["unit.yin.axe","unit.yin.axe","unit.yin.spear","unit.yin.spear"]:s.spawn(id,side,float(s.bases[side].x)+sign)
			s.spawn("unit.yin.worker",side,float(s.bases[side].x))
			var hidden=s.spawn("unit.yin.axe" if variant==0 else "unit.yin.cannon",1-side,float(s.bases[1-side].x)-sign)
			s.players[1-side].gold=0 if variant==0 else 9999;s.players[1-side].mana=0 if variant==0 else 100
			hidden.hp=1 if variant==0 else hidden.max_hp;s.visibility.refresh()
			check(not s.visible_to(side,hidden),"Mutated opponent remains outside current sight "+str(side)+" / "+str(variant))
			AI.turn(s,side)
			variants.append({"gold":p.gold,"queue":p.queue.duplicate(),"research":p.research.duplicate(true),"bank":p.get("ai_budget_bank",0),"target":p.get("ai_budget_study","")})
		check(variants[0]==variants[1],"Hidden opponent data cannot change own macro commands "+str(side))
		s=fixture(side);p=s.players[side]
		s.request(side,"recruit",{"id":"unit.yin.axe"})
		var copy=s.spawn("unit.yin.axe",side,float(s.bases[side].x),true)
		var scripted=s.spawn("unit.yin.axe",side,float(s.bases[side].x))
		var births: Array=s.drain_events()
		check(births.any(func(e):return e.kind=="spawn" and e.uid==copy.uid and e.get("origin","")=="clone"),"A clone birth is distinct from paid production "+str(side))
		check(births.any(func(e):return e.kind=="spawn" and e.uid==scripted.uid and e.get("origin","")=="scripted"),"Fixture births do not claim a recruitment receipt "+str(side))
		for i in range(125):s.tick(1.0/60.0)
		births=s.drain_events()
		check(births.any(func(e):return e.kind=="spawn" and e.side==side and e.id=="unit.yin.axe" and e.get("origin","")=="production" and e.uid not in [copy.uid,scripted.uid]),"Actual queue completion identifies the paid troop UID "+str(side))
		check(p.queue.is_empty() and is_equal_approx(float(p.gold),255+float(s.stats[side].gold_delivered)),"Birth annotation cannot create a free troop payment or change income "+str(side))
func paid_workflows():
	var db=Data.new()
	for faction in db.FACTIONS:
		var args=OS.get_cmdline_user_args()
		if args.has("--faction") and faction!=args[args.find("--faction")+1]:continue
		for side in [0,1]:
			var s=Simulation.new(db)
			s.start({"map":"map.01.01","faction":faction,"enemy":faction,"starting_gold":300,"enemy_starting_gold":300,"ai_warmup":0,"seed":137,"experimental_ai_budget_planner":true,"experimental_ai_budget_planner_side":side})
			s.ai_enabled=[side==0,side==1];s.drain_events()
			# Prevent an unopposed basic wave from ending the payment observation.
			# All treasury, workers, tech, production and prices remain unchanged.
			s.bases[1-side].hp=50000;s.bases[1-side].max_hp=50000
			var p: Dictionary=s.players[side];var node: Dictionary={}
			var started: float=-1;var completed: float=-1;var ordered: float=-1;var spawned: float=-1
			var crew: int=-1;var army: int=-1;var cash: float=300
			var ledger_ok: bool=true;var lock_ok: bool=true;var bank_ok: bool=true;var sequence_ok: bool=true
			for step in range(14400):
				s.tick(1.0/60.0)
				for e in s.drain_events():
					if int(e.get("side",-1))!=side:continue
					match e.kind:
						"gold":cash+=float(e.amount)
						"recruit":
							cash-=float(db.balance.units[e.id].gold)
							if not node.is_empty() and e.id==node.grant and ordered<0:ordered=float(e.time)
						"build":cash-=float(db.balance.buildings[e.id].gold)
						"research_start":
							cash-=float(db.tech(e.id).gold)
							if node.is_empty() and db.balance.units.has(db.tech(e.id).grant):
								node=db.tech(e.id);started=float(e.time);crew=s.population(side,true,true);army=s.population(side,false,true)
							elif not node.is_empty() and ordered<0:sequence_ok=false
						"research_done":
							if not node.is_empty() and e.id==node.grant:completed=float(e.time)
						"spawn":
							if not node.is_empty() and e.id==node.grant and ordered>=0 and e.get("origin","")=="production":spawned=float(e.time)
				ledger_ok=ledger_ok and is_equal_approx(float(p.gold),cash) and p.gold>=0
				bank_ok=bank_ok and float(p.get("ai_budget_bank",0))>=0 and float(p.get("ai_budget_bank",0))<=float(p.gold)+.001
				if not node.is_empty() and completed<0:lock_ok=lock_ok and not p.unlocked.has(node.grant)
				if spawned>=0 or s.winner!=-2:break
			var tag: String=faction+" / "+str(side)
			check(not node.is_empty(),"Normal mining starts a unit study "+tag)
			check(started>=0 and completed>=started+float(node.get("seconds",999))-.02,"Real study duration precedes unlock "+tag)
			check(ordered>=0 and ordered>=completed,"First advanced recruit is paid after the actual unlock "+tag)
			check(spawned>=0 and spawned>=ordered+float(db.balance.units.get(node.get("grant",""),{}).get("production_seconds",999))-.02,"Paid advanced order finishes normal production "+tag)
			check(ledger_ok,"Real income minus recruitment/research/build fees equals treasury "+tag)
			check(bank_ok,"Reserve remains a bounded claim on actual treasury "+tag)
			check(lock_ok,"Advanced unit stays locked during research "+tag)
			check(sequence_ok,"First paid deployment is not preempted by another study "+tag)
			check(crew>=5,"Paid non-rush growth crew precedes the first unit investment "+tag)
			check(army>=4,"Paid four-fighter opening precedes the first unit investment "+tag)
			cases.append({"faction":faction,"side":side,"study":node.get("id",""),"started":started,"completed":completed,"ordered":ordered,"spawned":spawned,"crew":crew,"army":army,"cash":p.gold,"reserve":p.get("ai_budget_bank",0),"waiting_study":p.get("ai_budget_study",""),"pending":p.get("ai_budget_unit",""),"queue":p.queue.duplicate(),"delivered":s.stats[side].gold_delivered})
func run():
	boundaries();paid_workflows()
	var args=OS.get_cmdline_user_args()
	if args.has("--output"):
		var file=FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE)
		var inputs: Dictionary={}
		for path in ["res://scripts/ai_budget_planner.gd","res://scripts/tactical_ai.gd","res://scripts/battle_sim.gd","res://scripts/unit_abilities.gd","res://scripts/map_runtime.gd","res://scripts/battle_visibility.gd","res://data/balance-prototype.json","res://data/technology.json","res://tests/test_ai_budget_planner.gd"]:inputs[path]=FileAccess.get_sha256(path)
		file.store_string(JSON.stringify({"scope":"Native CPU reserve, emergency-frontline, birth-origin and hidden-information boundary fixtures plus normal-resource paid workflows (240-second ceiling). Opposing combat AI disabled and endpoint HP extended to 50000 only in workflow fixtures. No treasury, unlock, research or production grants in workflows. Not opposing-AI balance, rendering or Android hardware evidence.","checks":checks,"failures":failures,"cases":cases,"inputs":inputs},"  "));file.close()
	print("AI_BUDGET_PLANNER: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
