extends SceneTree
# Legal player command scripts, not a new runtime AI or fixture-created armies.
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var db
var results: Array=[]
var next_research: float=25.0

func legal(s, kind: String, args: Dictionary) -> bool:
	return s.request(0,kind,args).ok

func control(s, variant: int):
	var p=s.players[0]
	var faction=p.faction
	var friends=[];var enemies=[];var frontline=[]
	for u in s.units:
		if db.balance.units[u.id].get("economy",false):continue
		if u.side==0:
			friends.append(u)
			if float(db.balance.units[u.id].range)<=1.2:frontline.append(u)
		else:enemies.append(u)
	var threat=enemies.any(func(u):return u.x<13)
	var order=db.unit_ids(faction)[0]
	var army=s.population(0,false)
	# Stabilise an early army, then invest in a legal worker advantage.
	if p.queue.size()<3 and army>=3 and s.population(0,true)<(4 if variant==1 else 6) and not threat and p.gold>=35:
		legal(s,"recruit",{"id":"unit."+faction+".worker"});return
	if faction=="deng" and army>=3 and p.gold>=(55 if variant==2 else 100):
		for slot in range(1 if variant==1 else 2):
			if not s.buildings.any(func(b):return b.side==0 and b.slot==slot):
				legal(s,"build",{"id":"building.deng.mana","slot":slot});return
	# Research only after a front exists; reserve the full cost rather than spam.
	var grants=[]
	if faction=="yin":grants=["unit.yin.spear","upgrade.yin.mana-1","unit.yin.hammer","spell.yin.lightning","unit.yin.cannon","upgrade.yin.mana-2","spell.yin.cold","spell.yin.stamp","spell.yin.fury"]
	elif faction=="mo":grants=["unit.mo.needle","spell.mo.bind","unit.mo.priest","spell.mo.poison","unit.mo.giant","spell.mo.convert","spell.mo.burst"]
	else:grants=["unit.deng.fire","unit.deng.shadow","unit.deng.effigy","spell.deng.clone","spell.deng.root","spell.deng.fire","spell.deng.guardian"]
	var reserve=false
	if army>=(4 if variant==0 else 2) and s.population(0,true)>=4 and not threat and p.research.is_empty() and s.time>=next_research:
		for grant in grants:
			if p.unlocked.has(grant):continue
			var tech=db.tech_for(grant)
			if not tech.requires.all(func(r):return p.studied.has(r)):continue
			if p.gold>=tech.gold:
				if legal(s,"research",{"id":tech.id}):next_research=s.time+25
			else:reserve=true
			break
	if not reserve and p.queue.size()<2:
		if frontline.size()>=2:
			var ids=db.unit_ids(faction)
			var index=(int(s.stats[0].recruited)%3)+1
			var candidate=ids[index]
			if p.unlocked.has(candidate):order=candidate
			if variant==1 and p.unlocked.has(ids[3]):order=ids[3]
			if order.ends_with("priest") and friends.any(func(u):return u.id.ends_with("priest")):order=ids[1]
		if p.gold>=db.balance.units[order].gold:legal(s,"recruit",{"id":order})
	# Pay only for a useful legal target and prioritise the front, not backline wounds.
	var wounded={};var closest={};var expensive={}
	for u in friends:
		if not u.clone and (wounded.is_empty() or u.max_hp-u.hp>wounded.max_hp-wounded.hp):wounded=u
	for u in enemies:
		if closest.is_empty() or u.x<closest.x:closest=u
		if expensive.is_empty() or db.balance.units[u.id].gold>db.balance.units[expensive.id].gold:expensive=u
	if faction=="yin":
		if not wounded.is_empty() and wounded.max_hp-wounded.hp>=70:legal(s,"cast",{"id":"spell.yin.repair","target":wounded.uid})
		if not closest.is_empty():
			var x=closest.x
			if s.area_units(x,2.2,1).size()>=3:legal(s,"cast",{"id":"spell.yin.stamp","x":x})
			if closest.id.ends_with("giant") or closest.x<13:legal(s,"cast",{"id":"spell.yin.lightning","target":closest.uid})
	elif faction=="mo":
		if not expensive.is_empty() and db.balance.units[expensive.id].gold>=90:legal(s,"cast",{"id":"spell.mo.convert","target":expensive.uid})
		if not closest.is_empty():
			if closest.windup>.25:legal(s,"cast",{"id":"spell.mo.bind","target":closest.uid})
			if s.area_units(closest.x,2.1,1).size()>=2:
				if not closest.statuses.has("poison"):legal(s,"cast",{"id":"spell.mo.poison","x":closest.x})
				elif p.mana>80:legal(s,"cast",{"id":"spell.mo.burst","x":closest.x})
	else:
		if not wounded.is_empty() and not closest.is_empty() and absf(wounded.x-closest.x)<2 and wounded.hp<wounded.max_hp*.55:legal(s,"cast",{"id":"spell.deng.protect","target":wounded.uid})
		var best={}
		for u in friends:
			if not u.clone and u.hp>u.max_hp*.75 and (best.is_empty() or db.balance.units[u.id].gold>db.balance.units[best.id].gold):best=u
		if not best.is_empty() and not closest.is_empty() and absf(best.x-closest.x)<5:legal(s,"cast",{"id":"spell.deng.clone","target":best.uid})
		if not closest.is_empty() and s.area_units(closest.x,2.0,1).size()>=2 and p.mana>65:legal(s,"cast",{"id":"spell.deng.fire","x":closest.x})

func _initialize():
	db=Data.new()
	var failed=[]
	for level in db.campaign:
		var args=OS.get_cmdline_user_args()
		if args.has("--level") and args[args.find("--level")+1]!=level.id:continue
		var attempts=[];var won=false
		for variant in range(3):
			var s=Simulation.new(db);s.start(level)
			next_research=25
			for i in range(60*600):
				if i%30==0:control(s,variant)
				s.tick(1.0/60);s.drain_events()
				if s.winner!=-2:break
			attempts.append({"variant":variant,"winner":s.winner,"seconds":snappedf(s.time,.1),"base_hp":[s.bases[0].hp,s.bases[1].hp],"stats":s.stats[0]})
			if s.winner==0:won=true;break
		results.append({"id":level.id,"legal_player_win":won,"attempts":attempts})
		print("CAMPAIGN_PATH "+JSON.stringify(results.back()))
		if not won:failed.append(level.id)
	var file=FileAccess.open("res://tests/campaign-path-report.json",FileAccess.WRITE)
	file.store_string(JSON.stringify({"results":results,"failures":failed,"method":"Only legal side-0 request commands; unmodified campaign starting resources and enemy AI."},"\t"));file.close()
	print("CAMPAIGN_PATHS "+JSON.stringify({"wins":results.size()-failed.size(),"failed":failed}))
	quit(0 if failed.is_empty() else 1)
