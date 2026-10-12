extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var failures: Array=[]
var records: Array=[]

func run():
	var args=OS.get_cmdline_user_args()
	if not args.has("--output"):push_error("--output is required");quit(1);return
	var maps: Array=["map.01.01","map.01.04","map.01.11"]
	var formal: bool=args.has("--formal-range")
	var ranges: Array=[float(Data.new().balance.units["unit.yin.hammer"].range)] if formal else [.82,1.25]
	for map_id in maps:
		for side in [0,1]:
			for mode in ["base","six-fronts"]:
				for reach in ranges:
					var db=Data.new()
					if not formal:db.balance.units["unit.yin.hammer"].range=reach
					var s=Simulation.new(db)
					s.start({"map":map_id,"faction":"yin","enemy":"yin","starting_gold":300,"enemy_starting_gold":300,"seed":271,"ai_warmup":0})
					s.ai_enabled=[false,false]
					# Only the stationary base fixture extends endpoint HP. No actors
					# are created, moved, unlocked or funded by this observation.
					if mode=="base":s.bases[1-side].hp=50000;s.bases[1-side].max_hp=50000
					var actor_sides: Dictionary={};var ledger: Array=[300.0,300.0]
					for u in s.units:actor_sides[u.uid]=u.side
					for b in s.bases:actor_sides[b.uid]=b.side
					s.drain_events()
					var commands: Array=[s.request(side,"research",{"id":"tech.yin.unit.hammer"}),s.request(side,"recruit",{"id":"unit.yin.axe"})]
					if mode=="six-fronts":
						for i in range(6):commands.append(s.request(1-side,"recruit",{"id":"unit.yin.axe"}))
					var ordered: bool=false;var uid: int=0;var hits: int=0;var releases: int=0
					var damage: float=0;var paid: Array=[];var born: float=-1;var first_hit: float=-1;var completed: float=-1;var ordered_at: float=-1
					var ledger_ok: bool=true;var friend_ok: bool=true;var samples: Array=[]
					for step in range(160*60):
						if not ordered and s.players[side].unlocked.has("unit.yin.hammer"):
							var result: Dictionary=s.request(side,"recruit",{"id":"unit.yin.hammer"});commands.append(result);ordered=result.ok
							if ordered:ordered_at=s.time
						s.tick(1.0/60.0)
						for e in s.drain_events():
							var team: int=int(e.get("side",-1))
							if e.kind=="research_done" and team==side and e.id=="unit.yin.hammer":completed=e.time
							if e.kind=="spawn":
								actor_sides[e.uid]=team
								if team==side and e.id=="unit.yin.hammer" and e.get("origin","")=="production" and uid==0:uid=int(e.uid);born=float(e.time)
							if team in [0,1] and e.kind=="gold":ledger[team]+=float(e.amount)
							if team in [0,1] and e.kind in ["research_start","recruit"]:
								var fee: float=float(db.tech(e.id).gold) if e.kind=="research_start" else float(db.balance.units[e.id].gold)
								ledger[team]-=fee;paid.append({"kind":e.kind,"id":e.id,"side":team,"time":e.time,"gold_spent":fee})
							if e.kind=="attack_release" and int(e.uid)==uid:releases+=1
							if e.kind=="hit":
								var target_side: int=int(actor_sides.get(int(e.uid),-1))
								friend_ok=friend_ok and target_side in [0,1] and int(e.side)==target_side and int(e.attacker_side)!=target_side
								if uid!=0 and int(e.get("source_uid",0))==uid and int(e.get("attacker_side",-1))==side:
									hits+=1;damage+=float(e.amount)
									if first_hit<0:first_hit=float(e.time)
						for team_id in [0,1]:ledger_ok=ledger_ok and is_equal_approx(float(s.players[team_id].gold),float(ledger[team_id])) and s.players[team_id].gold>=0
						if uid!=0 and step%600==599:
							var h: Dictionary=s.actor(uid)
							if not h.is_empty():
								var nearest: Dictionary=s.nearest_enemy(h)
								var distance: float=-1 if nearest.is_empty() else s.combat_distance(h,nearest,db.balance.units[h.id])
								var ahead: Array=[]
								for u in s.units:
									if u.side==side and u.hp>0 and u.uid!=uid and not db.balance.units[u.id].get("economy",false) and u.edge==h.edge and (u.s-h.s)*(1 if side==0 else -1)>0:ahead.append({"uid":u.uid,"id":u.id,"gap":absf(u.s-h.s),"hp":u.hp})
								samples.append({"time":s.time,"x":h.x,"edge":h.edge,"s":h.s,"hp":h.hp,"anim":h.anim,"target":h.target,"nearest_uid":nearest.get("uid",0),"nearest_distance":distance,"allies_ahead":ahead})
						if s.winner!=-2 or (uid!=0 and s.actor(uid).is_empty() and s.players[side].queue.is_empty()):break
					var ok: bool=commands.all(func(c):return c.ok) and ledger_ok and friend_ok and uid!=0
					if not ok:failures.append({"map":map_id,"side":side,"mode":mode,"reach":reach,"commands":commands,"ledger_ok":ledger_ok,"friend_ok":friend_ok,"uid":uid})
					records.append({"map":map_id,"side":side,"mode":mode,"range_override":null if formal else reach,"effective_range":reach,"paid_uid":uid,"research_completed":completed,"ordered_at":ordered_at,"born":born,"first_hit":first_hit,"hits":hits,"attack_releases":releases,"event_damage":damage,"time":s.time,"paid":paid,"ledger_ok":ledger_ok,"friend_ok":friend_ok,"samples":samples})
	var inputs: Dictionary={}
	for path in ["res://scripts/battle_sim.gd","res://scripts/battle_command_rules.gd","res://scripts/tactical_ai.gd","res://scripts/ai_budget_planner.gd","res://scripts/map_runtime.gd","res://scripts/battle_visibility.gd","res://data/balance-prototype.json","res://data/technology.json","res://data/maps.json"]:inputs[path]=FileAccess.get_sha256(path)
	var file=FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE)
	if file==null:push_error("Cannot write requested report");quit(1);return
	var scope: String="Windows native CPU isolated paid hammer plus one basic escort, all three road lengths and both sides. Opposing AI/spells disabled; stationary base fixture alone extends endpoint HP to50000. Six-front recipe retains normal endpoint HP and buys six actual45-gold opponents. "+("Formal default reach is read without an override. " if formal else "Runtime-only .82/1.25 reach controls. ")+"Normal300-gold treasury, mining,66-gold research,95-gold production and formal fog. No actor placement, gifts or free unlocks. Not default AI, rendering, faction balance or Android hardware evidence."
	file.store_string(JSON.stringify({"scope":scope,"formal_default":formal,"passed":failures.is_empty(),"failures":failures,"records":records,"inputs":inputs,"observer_sha256":FileAccess.get_sha256(get_script().resource_path)},"  "));file.close()
	print("PAID_HAMMER_SCREEN: ",records.size()," recipes; failures=",failures)
	quit(0 if failures.is_empty() else 1)

func _initialize():call_deferred("run")
