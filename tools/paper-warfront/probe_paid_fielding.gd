extends SceneTree
# Paid integration flow; the opposing AI is disabled to isolate investment order.
# This is not a matchup, original-game timing or balance acceptance probe.
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var checks: int=0
var failures: Array=[]
var cases: Array=[]
var hold_opening_fixture: bool=false
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func flow(side: int,faction: String,trial: bool):
	var sim=Simulation.new(Data.new())
	sim.start({"map":"map.01.20","faction":faction if side==0 else "yin","enemy":"yin" if side==0 else faction,"starting_gold":160,"enemy_starting_gold":160,"ai_warmup":0,"seed":137})
	sim.ai_enabled=[false,false]
	if trial:
		sim.config["experimental_ai_grant_redemption"]=true
		sim.config["experimental_ai_grant_redemption_side"]=side
	var p: Dictionary=sim.players[side]
	var label: String=faction+" / "+str(side)
	var opening: Array=[]
	for id in p.roster:
		if p.unlocked.has(id) and not sim.db.balance.units[id].get("economy",false):opening.append(id)
	verify(opening.size()>=2,"Two starting combat roles exist / "+label)
	var paid: float=0
	for id in opening.slice(0,2):
		verify(sim.request(side,"recruit",{"id":id}).ok,"Opening fighter pays its actual fee / "+label+" / "+id)
		paid+=float(sim.db.balance.units[id].gold)
	verify(is_equal_approx(float(p.gold),160-paid),"160-gold opening ledger / "+label)
	sim.drain_events()
	while sim.time<5:sim.tick(1.0/60.0)
	verify(sim.population(side,false,false)==2,"Opening fighters pass real production timers / "+label)
	if hold_opening_fixture:
		# Explicit position/status fixture: prevent a victory before enough real
		# transport income arrives. Neither cash nor production is modified.
		for u in sim.units:
			if u.side==side and not sim.db.balance.units[u.id].get("economy",false):sim.set_status(u,"bind",180,0)
	sim.drain_events();sim.ai_enabled[side]=true
	var first: Dictionary={}
	var ledger_valid: bool=true
	var next_study_before_first_order: bool=false
	var order_count: int=0
	while sim.time<180 and sim.winner==-2:
		sim.tick(1.0/60.0)
		for e in sim.drain_events():
			if int(e.get("side",-1))!=side:continue
			if e.kind=="recruit":
				paid+=float(sim.db.balance.units[e.id].gold)
				if not first.is_empty() and e.id==first.grant and first.get("order_at",-1.0)<0:
					first["order_at"]=float(e.time);order_count+=1
			if e.kind=="build":paid+=float(sim.db.balance.buildings[e.id].gold)
			if e.kind=="research_start":
				var node: Dictionary=sim.db.tech(e.id)
				paid+=float(node.gold)
				if first.is_empty() and sim.db.balance.units.has(node.grant):
					first={"tech":node.id,"grant":node.grant,"research_at":float(e.time),"research_seconds":float(node.seconds),"unit_price":float(sim.db.balance.units[node.grant].gold),"production_seconds":float(sim.db.balance.units[node.grant].production_seconds)}
				elif not first.is_empty() and first.get("order_at",-1.0)<0:next_study_before_first_order=true
			if not first.is_empty() and e.kind=="research_done" and e.id==first.grant:first["completed_at"]=float(e.time)
			if not first.is_empty() and e.kind=="spawn" and e.id==first.grant and e.get("origin","")=="production":
				first["spawn_at"]=float(e.time);first["uid"]=int(e.uid)
		ledger_valid=ledger_valid and is_equal_approx(float(p.gold),160+float(sim.stats[side].gold_delivered)-paid)
		if first.has("spawn_at"):break
	verify(float(sim.stats[side].gold_delivered)>0,"Subsequent purchases use real delivered ore / "+label)
	verify(ledger_valid and p.gold>=0,"Every actual gold payment balances without a free grant / "+label)
	verify(not first.is_empty(),"A paid unit research starts in the controlled flow / "+label)
	verify(first.has("completed_at"),"The paid study actually completes / "+label)
	verify(first.has("order_at"),"The researched unit receives an actual paid order / "+label)
	verify(first.has("spawn_at"),"The paid order actually produces its own unit / "+label)
	verify(not next_study_before_first_order,"Another study cannot displace the first recruit / "+label)
	if first.has("completed_at"):
		verify(float(first.completed_at)-float(first.research_at)>=float(first.research_seconds)-.001,"No shortcut around research time / "+label)
	if first.has("order_at") and first.has("completed_at"):
		verify(float(first.order_at)>=float(first.completed_at),"Recruitment waits for the actual unlock / "+label)
	if first.has("spawn_at") and first.has("order_at"):
		verify(float(first.spawn_at)-float(first.order_at)>=float(first.production_seconds)-.001,"No shortcut around queued production / "+label)
		var actor: Dictionary=sim.actor(int(first.uid))
		verify(not actor.is_empty() and actor.side==side and actor.id==first.grant,"Correct production UID and ownership / "+label)
	verify(order_count<=1,"The observed first delivery has one paid order / "+label)
	cases.append({"faction":faction,"side":side,"time":sim.time,"winner":sim.winner,"gold":p.gold,"gold_delivered":sim.stats[side].gold_delivered,"gold_spent":paid,"ledger_valid":ledger_valid,"first":first})
func run():
	var args: PackedStringArray=OS.get_cmdline_user_args()
	hold_opening_fixture=args.has("--hold-opening-fixture")
	for faction in ["yin","mu","bai"]:
		for side in [0,1]:flow(side,faction,args.has("--trial"))
	var report: Dictionary={"passed":failures.is_empty(),"scope":"Native Windows paid first-research/order/production integration; 160 starting gold, actual transport and fees. Opposing AI disabled, so this is not balance acceptance.","checks":checks,"failures":failures,"cases":cases,"observer_sha256":FileAccess.get_sha256(get_script().resource_path)}
	report["opening_fighters_immobilized_fixture"]=hold_opening_fixture
	if args.has("--output"):
		var file=FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE)
		if file==null:push_error("Cannot write paid-fielding report");quit(1);return
		file.store_string(JSON.stringify(report,"  "))
	print("PAID_FIELDING_FLOW: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
