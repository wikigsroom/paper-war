extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var checks: int=0
var failures: Array=[]
var cases: Array=[]
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func _initialize():call_deferred("run")
func run():
	var db=Data.new()
	for faction in db.FACTIONS:
		for side in [0,1]:
			var s=Simulation.new(db)
			s.start({"map":"map.01.01","faction":faction,"enemy":faction,"starting_gold":300,"enemy_starting_gold":300,"ai_warmup":0,"seed":137,"experimental_ai_paid_opening":true})
			s.ai_enabled=[side==0,side==1];s.drain_events()
			# An unopposed basic wave can destroy the ordinary endpoint before a
			# late study finishes. This fixture extends the endpoint's health, not
			# either treasury, research, production or worker income.
			s.bases[1-side].hp=20000.0;s.bases[1-side].max_hp=20000.0
			var p: Dictionary=s.players[side]
			var node: Dictionary={};var started: float=-1;var completed: float=-1;var ordered: float=-1;var spawned: float=-1
			var starting_crew: int=-1;var starting_army: int=-1
			var cash: float=300;var ledger_ok: bool=true;var locked_ok: bool=true;var reserve_ok: bool=true;var sequence_ok: bool=true
			# The crew and basic wave are now paid before the first study. Allow
			# their actual mining cycles to fund the more expensive faction kits.
			for step in range(7200):
				s.tick(1.0/60.0)
				for e in s.drain_events():
					if int(e.get("side",-1))!=side:continue
					if e.kind=="gold":cash+=float(e.amount)
					if e.kind=="recruit":
						cash-=float(db.balance.units[e.id].gold)
						if not node.is_empty() and e.id==node.grant and ordered<0:ordered=float(e.time)
					if e.kind=="research_start":
						cash-=float(db.tech(e.id).gold)
						if node.is_empty():
							node=db.tech(e.id);started=float(e.time)
							starting_crew=s.population(side,true,true);starting_army=s.population(side,false,true)
						elif ordered<0:sequence_ok=false
					if e.kind=="research_done" and not node.is_empty() and e.id==node.grant:completed=float(e.time)
					if e.kind=="spawn" and not node.is_empty() and e.id==node.grant and ordered>=0:spawned=float(e.time)
				ledger_ok=ledger_ok and is_equal_approx(float(p.gold),cash) and p.gold>=0
				if not node.is_empty() and completed<0:
					locked_ok=locked_ok and not p.unlocked.has(node.grant)
					reserve_ok=reserve_ok and p.gold>=float(db.balance.units[node.grant].gold)
				if spawned>=0 or s.winner!=-2:break
			var tag: String=faction+" side "+str(side)
			check(not node.is_empty() and str(node.get("grant","")).begins_with("unit."),tag+": normal resources start a unit study")
			check(completed>=started+float(node.get("seconds",999))-.02,tag+": study completes after its real duration")
			check(ordered>=completed and ordered>=0,tag+": first unit is paid only after unlock")
			check(spawned>=ordered+float(db.balance.units.get(node.get("grant",""),{}).get("production_seconds",999))-.02,tag+": paid unit completes normal production")
			check(ledger_ok,tag+": delivered gold minus real command fees equals cash")
			check(locked_ok,tag+": advanced unit stays locked during study")
			check(reserve_ok,tag+": first recruitment money remains funded during study")
			check(sequence_ok,tag+": another study does not preempt first deployment")
			check(starting_crew>=3,tag+": three paid miners precede technology savings")
			check(starting_army>=3,tag+": three paid basic fighters precede technology savings")
			cases.append({"faction":faction,"side":side,"study":node.get("id",""),"started":started,"completed":completed,"ordered":ordered,"spawned":spawned,"starting_crew":starting_crew,"starting_army":starting_army,"gold":p.gold})
	var args=OS.get_cmdline_user_args()
	if args.has("--output"):
		var file=FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE)
		file.store_string(JSON.stringify({"scope":"Twenty side-scoped native normal-resource workflows, 120-second ceiling, crew and basic wave paid first, opposing combat AI disabled, opposing endpoint HP extended to 20000. No treasury or research grants. Controlled payment fixture, not ordinary opposing-AI balance, rendering or Android evidence.","checks":checks,"failures":failures,"cases":cases},"  "));file.close()
	print("PAID_OPENING: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
