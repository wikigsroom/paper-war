extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var db
var passed: int = 0
var failures: Array = []
var campaign_results: Array = []

func check(condition: bool, name_value: String):
	if condition: passed+=1; print("PASS "+name_value)
	else: failures.append(name_value); push_error("FAIL "+name_value)

func battle(f: String = "yin", e: String = "mo", full: bool = true):
	var s=Simulation.new(db)
	s.start({"map":"map.01.01","faction":f,"enemy":e,"full_tech":full,"starting_gold":500,"enemy_starting_gold":500,"difficulty":1,"ai_warmup":0})
	s.ai_enabled=[false,false]
	return s

func advance(s, seconds: float):
	for i in range(int(seconds*60)):
		s.tick(1.0/60); s.drain_events()

func _initialize():
	db=Data.new()
	var s=battle()
	var gold=s.players[0].gold
	var result=s.command(0,1,"recruit",{"id":"unit.yin.axe"})
	check(result.ok and s.players[0].gold==gold-45,"recruit charges exact gold")
	result=s.command(0,1,"recruit",{"id":"unit.yin.axe"})
	check(not result.ok and s.players[0].queue.size()==1 and s.players[0].gold==gold-45,"duplicate command cannot spend twice")
	s.request(0,"cancel_queue",{"index":0})
	check(s.players[0].gold==gold and s.players[0].queue.is_empty(),"unspawned order refund")
	s=battle("yin","mo",false)
	# Selected opening roles are unlocked in 3.0. Explicitly lock this research
	# fixture rather than treating an already-known technology as researchable.
	var spear_tech: Dictionary=db.tech_for("unit.yin.spear")
	s.players[0].unlocked.erase("unit.yin.spear");s.players[0].studied.erase(spear_tech.id)
	gold=s.players[0].gold
	check(not s.request(0,"recruit",{"id":"unit.yin.cannon"}).ok and s.players[0].gold==gold,"locked recruitment is atomic")
	var advanced: Dictionary=db.technology.nodes.filter(func(node):return node.faction=="yin" and not node.requires.is_empty())[0]
	for required in advanced.requires:s.players[0].studied.erase(required)
	check(not s.request(0,"research",{"id":advanced.id}).ok and s.players[0].gold==gold,"technology prerequisite enforced")
	check(s.request(0,"research",{"id":spear_tech.id}).ok,"technology starts")
	advance(s,float(spear_tech.seconds)+.1)
	check(s.players[0].unlocked.has("unit.yin.spear"),"technology completes after time")
	s=battle()
	gold=s.players[0].gold
	advance(s,3)
	check(s.players[0].gold==gold,"gold not credited before delivery")
	advance(s,7)
	check(s.players[0].gold>gold and s.stats[0].gold_delivered>0,"worker deposits cargo")
	s=battle(); var ally=s.spawn("unit.yin.axe",0,20); var enemy=s.spawn("unit.mo.blade",1,23)
	var mana=s.players[0].mana
	check(not s.request(0,"cast",{"id":"spell.yin.repair","target":enemy.uid,"x":23}).ok and s.players[0].mana==mana,"wrong target does not spend mana")
	ally.hp=35; s.players[0].mana=100
	check(s.request(0,"cast",{"id":"spell.yin.repair","target":ally.uid,"x":20}).ok and ally.hp==120,"repair heals 85")
	check(not s.request(0,"cast",{"id":"spell.yin.repair","target":ally.uid,"x":20}).ok,"cooldown rejects duplicate cast")
	s=battle("mo","yin"); ally=s.spawn("unit.mo.blade",0,20); ally.hp=50; s.players[0].mana=0
	check(s.request(0,"cast",{"id":"spell.mo.sacrifice","target":ally.uid,"x":20}).ok and s.players[0].mana==9 and s.corpses.is_empty(),"sacrifice uses remaining hp and creates no corpse")
	check(not s.request(0,"cast",{"id":"spell.mo.sacrifice","target":s.units[0].uid,"x":3}).ok,"worker cannot be sacrificed")
	s=battle("deng","yin"); ally=s.spawn("unit.deng.mirror",0,20); s.players[0].mana=100
	s.request(0,"cast",{"id":"spell.deng.clone","target":ally.uid,"x":20})
	var copy=s.units.back()
	check(copy.clone and copy.ttl==10,"clone has finite lifetime")
	s.players[0].cooldowns["spell.deng.clone"]=0
	check(not s.request(0,"cast",{"id":"spell.deng.clone","target":copy.uid,"x":20}).ok,"clone chain rejected")
	s.die(copy,true); check(s.corpses.is_empty(),"clone leaves no reusable corpse")
	s=battle("deng","yin"); mana=s.mana_rate(0); gold=s.players[0].gold
	check(s.request(0,"build",{"id":"building.deng.mana","slot":0}).ok and is_equal_approx(s.mana_rate(0),mana),"unfinished paper lamp supplies no mana")
	advance(s,4.2);check(is_equal_approx(s.mana_rate(0),mana+1.1),"finished paper lamp supplies mana")
	check(not s.request(0,"build",{"id":"building.deng.mana","slot":0}).ok and s.players[0].gold==gold-55,"occupied slot cannot charge twice")
	s.damage(s.buildings[0],1000,1,false)
	check(is_equal_approx(s.mana_rate(0),mana),"destroyed lamp stops mana immediately")
	s=battle("deng","yin"); ally=s.spawn("unit.deng.mirror",0,20); enemy=s.spawn("unit.yin.spear",1,23); ally.special_cd=0
	s.launch(enemy,ally,14,0,1,0); advance(s,.6)
	check(s.stats[0].reflections==1 and enemy.hp<enemy.max_hp and ally.hp==ally.max_hp,"projectile reflects exactly once")
	s=battle("mo","yin"); var priest=s.spawn("unit.mo.priest",0,20); enemy=s.spawn("unit.yin.axe",1,20.4)
	s.die(enemy,true); priest.summon_cd=0; advance(s,.05)
	check(s.stats[0].summons==1 and s.corpses.is_empty(),"priest consumes corpse once")
	s=battle("deng","mo"); ally=s.spawn("unit.deng.mirror",0,20); s.players[0].mana=100
	s.request(0,"cast",{"id":"spell.deng.protect","target":ally.uid,"x":20}); s.damage(ally,100,1,true)
	check(ally.hp==ally.max_hp,"protection blocks damage")
	s=battle("yin","mo"); enemy=s.spawn("unit.mo.giant",1,20); enemy.windup=.4
	s.set_status(enemy,"stun",.4); advance(s,.02)
	check(enemy.windup==0 and s.stats[0].interrupts>0,"control interrupts giant windup")
	s=battle(); s.bases[0].hp=0;s.bases[1].hp=0;s.tick(.01)
	check(s.winner==-1,"simultaneous bases destroyed is draw")
	check(not s.request(0,"recruit",{"id":"unit.yin.axe"}).ok,"commands freeze after result")
	s=battle("mo","yin"); enemy=s.spawn("unit.yin.hammer",1,20);s.players[0].mana=100
	check(s.request(0,"cast",{"id":"spell.mo.convert","target":enemy.uid,"x":20}).ok and enemy.side==0 and enemy.id=="unit.yin.hammer","conversion preserves native unit abilities")
	s=battle("deng","mo");enemy=s.spawn("unit.mo.giant",1,20);s.players[0].mana=100
	check(not s.request(0,"cast",{"id":"spell.deng.clone","target":enemy.uid,"x":20}).ok,"enemy and giant cannot be cloned")
	ally=s.spawn("unit.mo.giant",0,20)
	check(not s.request(0,"cast",{"id":"spell.deng.clone","target":ally.uid,"x":20}).ok,"friendly giant cannot be cloned")
	s=battle("yin","mo");enemy=s.spawn("unit.mo.giant",1,25);var far=s.spawn("unit.mo.blade",1,29);s.players[0].mana=100
	var giant_hp: float=enemy.hp
	s.request(0,"cast",{"id":"spell.yin.stamp","x":25});advance(s,.4)
	check(enemy.hp==giant_hp,"stamp damage waits for visible anticipation")
	advance(s,.2);check(enemy.hp==giant_hp-135 and far.hp==far.max_hp,"stamp applies exact radius and damage")
	s=battle("deng","yin");enemy=s.spawn("unit.yin.hammer",1,25);s.players[0].mana=100
	s.request(0,"cast",{"id":"spell.deng.fire","x":25});advance(s,1.1)
	check(enemy.hp==132,"fire produces three timed pulses")
	s=battle("mo","yin");enemy=s.spawn("unit.yin.hammer",1,25);far=s.spawn("unit.yin.hammer",1,30);s.players[0].mana=100
	s.request(0,"cast",{"id":"spell.mo.burst","x":25,"target":far.uid})
	check(enemy.hp==130 and far.hp==240,"area spell keeps chosen ground point despite supplied unit target")
	s=battle("yin","mo");ally=s.spawn("unit.yin.axe",0,20);enemy=s.spawn("unit.mo.giant",1,20.4);s.players[0].mana=100
	giant_hp=enemy.hp
	s.request(0,"cast",{"id":"spell.yin.fury","target":ally.uid,"x":20});s.attack(ally,enemy)
	check(is_equal_approx(enemy.hp,giant_hp-18*1.4),"fury multiplies damage once")
	s=battle("mo","yin");enemy=s.spawn("unit.yin.hammer",1,25);s.players[0].mana=100
	s.request(0,"cast",{"id":"spell.mo.poison","x":25});s.set_status(enemy,"poison",3,4,0);advance(s,1)
	check(is_equal_approx(enemy.hp,228),"poison uses strongest source without stacking")
	s=battle("deng","yin");enemy=s.spawn("unit.yin.axe",1,25);s.players[0].mana=100
	s.request(0,"cast",{"id":"spell.deng.root","target":enemy.uid,"x":25});var previous=enemy.x;advance(s,.5)
	check(enemy.x==previous,"root stops movement")
	s=battle("yin","deng");enemy=s.spawn("unit.deng.shadow",1,20.8);ally=s.spawn("unit.yin.axe",0,20);enemy.special_cd=0;s.set_status(enemy,"root",2);previous=enemy.x;advance(s,.1)
	check(enemy.x==previous,"root also prevents shadow crossing")
	s=battle("yin","mo");var cannon=s.spawn("unit.yin.cannon",0,49);s.launch(cannon,s.bases[1],38,.55,2.5,0);advance(s,.5)
	check(s.bases[1].hp==1005,"cannon applies building multiplier once")
	s=battle("deng","yin");s.request(0,"build",{"id":"building.deng.tower","slot":1})
	check(s.stats[0].build_counts.get("building.deng.mana",0)==0,"tower does not satisfy lamp challenge")
	s.request(0,"build",{"id":"building.deng.mana","slot":0})
	check(s.stats[0].build_counts.get("building.deng.mana",0)==1,"lamp challenge tracks correct building type")
	s=battle();s.config.win="survive";s.config.duration=1.0;advance(s,1.1)
	check(s.winner==0 and s.bases[0].hp>0,"survival challenge awards victory after deadline")
	s=battle("deng","yin");s.players[0].mana=100
	check(not s.request(0,"cast",{"id":"spell.deng.guardian","x":s.bases[1].x-.5}).ok and s.players[0].mana==100,"guardian cannot be placed inside enemy base")
	check(s.request(0,"cast",{"id":"spell.deng.guardian","x":26}).ok,"guardian summons at legal position")
	advance(s,8.1)
	check(not s.units.any(func(u):return u.id=="unit.deng.guardian"),"guardian expires without reusable corpse")
	s=battle();var worker=s.units[0];worker.cargo=8;gold=s.players[0].gold;s.die(worker,false)
	check(s.players[0].gold==gold,"dead worker loses undelivered cargo")
	var replay_a=battle();var replay_b=battle();replay_a.ai_enabled=[true,true];replay_b.ai_enabled=[true,true]
	advance(replay_a,50);advance(replay_b,50)
	check(JSON.stringify(replay_a.units)==JSON.stringify(replay_b.units) and JSON.stringify(replay_a.players)==JSON.stringify(replay_b.players),"identical seed and commands reproduce state")
	for f in db.FACTIONS:
		s=battle(f,"yin")
		for i in range(2):s.spawn("unit."+f+".worker",0,s.bases[0].x+.4)
		for i in range(6): s.request(0,"recruit",{"id":"unit."+f+".worker"})
		gold=s.players[0].gold
		check(s.population(0,true)==10 and not s.request(0,"recruit",{"id":"unit."+f+".worker"}).ok and s.players[0].gold==gold,"worker cap reserves queued population "+f)
	if OS.get_cmdline_user_args().has("--campaign"):
		for level in db.campaign:
			s=Simulation.new(db); s.start(level); s.ai_enabled=[true,true]
			for i in range(60*540):
				s.tick(1.0/60); s.drain_events()
				if s.winner!=-2: break
			campaign_results.append({"id":level.id,"winner":s.winner,"seconds":snappedf(s.time,.1),"base_hp":[s.bases[0].hp,s.bases[1].hp],"stats":s.stats})
			check(s.winner!=-2,"campaign match reaches result "+level.id)
			print("MATCH "+JSON.stringify(campaign_results.back()))
	var report={"passed":passed,"failures":failures,"campaign":campaign_results,"engine":Engine.get_version_info(),"inputs":{}}
	for path in ["res://data/balance-prototype.json","res://data/maps.json","res://scripts/battle_sim.gd","res://scripts/map_runtime.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var args=OS.get_cmdline_user_args();var destination: String=args[args.find("--output")+1] if args.has("--output") else "res://tests/simulation-report.json"
	var file=FileAccess.open(destination,FileAccess.WRITE); file.store_string(JSON.stringify(report,"\t")); file.close()
	print("SIMULATION_TESTS "+JSON.stringify({"passed":passed,"failed":failures.size()}))
	quit(0 if failures.is_empty() else 1)
