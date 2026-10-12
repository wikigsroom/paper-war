extends SceneTree
const Store = preload("res://scripts/data_store.gd")
const Simulation = preload("res://scripts/battle_sim.gd")
var failures: Array = []
var results: Array = []
var checks: int = 0

func verify(condition: bool,message: String):
	checks+=1
	if not condition:failures.append(message);print("FAIL ",message)

func measure(db,workers: int,side: int) -> Dictionary:
	var sim=Simulation.new(db)
	sim.start({"map":"map.01.07","faction":"yin","enemy":"yin","starting_gold":0,"enemy_starting_gold":0})
	sim.ai_enabled=[false,false];sim.units.clear();sim.drain_events()
	for i in range(workers):sim.spawn("unit.yin.worker",side,sim.bases[side].x+.1*(1 if side==0 else -1))
	var mining_peak: Dictionary = {};var delivered: Dictionary = {};var deposit_uids: Dictionary = {}
	for tick in range(180*60):
		sim.tick(1.0/60.0)
		for event in sim.drain_events():
			if event.kind=="gold" and event.side==side:
				delivered[event.mine]=int(delivered.get(event.mine,0))+int(event.amount)
				deposit_uids[event.uid]=int(deposit_uids.get(event.uid,0))+1
		for mine in sim.map.definition.mines:
			var active: int = int(sim.mine_state(mine).active)
			mining_peak[mine.id]=maxi(active,int(mining_peak.get(mine.id,0)))
			var problem: String = "More mining workers than service slots: "+mine.id+" workers="+str(workers)
			if active>int(mine.capacity) and not failures.has(problem):verify(false,problem)
	verify(deposit_uids.size()==workers,"Every assigned worker makes deposits: %d side %d"%[workers,side])
	return {"workers":workers,"side":side,"gold":sim.stats[side].gold_delivered,"by_mine":delivered,"mining_peak":mining_peak,"worker_trips":deposit_uids}

func paid_measure(db,extra: int) -> Dictionary:
	var sim=Simulation.new(db)
	sim.start({"map":"map.01.07","faction":"yin","enemy":"yin","starting_gold":230,"enemy_starting_gold":230})
	sim.ai_enabled=[false,false];sim.drain_events()
	var expense: float=extra*float(db.balance.units["unit.yin.worker"].gold)
	for side in [0,1]:
		for i in range(extra):verify(sim.request(side,"recruit",{"id":"unit.yin.worker"}).ok,"Paid worker recruitment %d side %d"%[extra,side])
		verify(is_equal_approx(sim.players[side].gold,230-expense),"Investment charges actual worker cost")
	var samples: Array=[]
	for tick in range(180*60):
		sim.tick(1.0/60.0);sim.drain_events()
		if (tick+1)%60==0:samples.append([sim.players[0].gold,sim.players[1].gold])
	verify(sim.population(0,true)==extra+2 and sim.players[0].queue.is_empty(),"Paid production finishes all workers")
	verify(absf(sim.players[0].gold-sim.players[1].gold)<=8,"Paid investment mirror within one cargo")
	return {"extra_workers":extra,"expense_each_side":expense,"starting_gold":230,"end_gold":[sim.players[0].gold,sim.players[1].gold],"gold_delivered":[sim.stats[0].gold_delivered,sim.stats[1].gold_delivered],"samples_each_second":samples}

func _init():
	var db=Store.new()
	for side in [0,1]:
		for count in [2,3,4,6]:results.append(measure(db,count,side))
	for i in range(4):
		verify(results[i].gold==results[i+4].gold,"Symmetric income with same faction/worker budget "+str(i))
	var three: Dictionary = results[1];var four: Dictionary = results[2];var six: Dictionary = results[3]
	verify(int(four.by_mine.get("mine.0.1",0))>0,"Fourth worker opens sustained outer-mine income")
	verify(four.gold>three.gold,"Adding external economy increases total income")
	verify(six.gold>four.gold,"Additional outer workers increase total income")
	var investments: Array=[]
	for extra in [0,1,2,4]:investments.append(paid_measure(db,extra))
	var control: Dictionary=investments[0]
	for investment in investments:
		var first: int=-1;var last_below: int=0
		for i in range(investment.samples_each_second.size()):
			if investment.samples_each_second[i][0]>=control.samples_each_second[i][0]:
				if first<0:first=i+1
			else:last_below=i+1
		investment["first_break_even_second"]=first
		investment["no_further_shortfall_in_180s_after_second"]=last_below+1 if last_below<180 else -1
		investment["net_advantage_at_180s"]=investment.end_gold[0]-control.end_gold[0]
	var sim=Simulation.new(db);sim.start({"map":"map.01.01","faction":"yin","enemy":"yin","full_tech":true,"starting_gold":500})
	verify(not sim.request(0,"build",{"id":"building.yin.tower","slot":0}).ok,"Rear mana-only site rejects a tower")
	verify(sim.request(0,"build",{"id":"building.yin.mana","slot":0}).ok,"Rear mana site accepts its facility")
	verify(sim.request(0,"build",{"id":"building.yin.tower","slot":1}).ok,"Front defense site accepts its tower")
	var report: Dictionary = {"scope":"Authored W02: controlled preplaced-worker throughput plus legal paid recruitment/production investment under equal230 gold, two normal opening workers, no combat. Break-even sampled each second for180s; not safe profit under harassment, strategic win-rate or human QA.","passed":failures.is_empty(),"checks":checks,"failures":failures,"results":results,"paid_investments":investments,"engine":Engine.get_version_info(),"inputs":{}}
	for path in ["res://data/maps.json","res://data/balance-prototype.json","res://scripts/map_runtime.gd","res://scripts/battle_sim.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var args=OS.get_cmdline_user_args();var destination: String = args[0] if not args.is_empty() else "res://tests/theatre-economy-report.json"
	var file=FileAccess.open(destination,FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("THEATRE_ECONOMY ",JSON.stringify({"passed":report.passed,"failures":failures,"results":results}))
	quit(0 if failures.is_empty() else 1)
