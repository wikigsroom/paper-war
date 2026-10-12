extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
func controller(s,metric: String):
	var p: Dictionary=s.players[0]
	var allies: Array=[];var enemies: Array=[];var counts: Dictionary={}
	for u in s.units:
		if u.hp<=0:continue
		if u.side==0:
			counts[u.id]=int(counts.get(u.id,0))+1
			if not s.db.balance.units[u.id].get("economy",false):allies.append(u)
		elif s.visible_to(0,u) and not s.db.balance.units[u.id].get("economy",false):enemies.append(u)
	for id in p.queue:counts[id]=int(counts.get(id,0))+1
	if metric=="facility_mana":
		for slot in range(s.side_sites(0).size()):
			var site: Dictionary=s.slot_anchor(0,slot)
			if site.get("types",[]).has("mana"):
				if s.request(0,"build",{"id":"building.deng.mana","slot":slot}).ok:break
	var plan: Array=[]
	match metric:
		"summons":plan=["giant","priest","needle","blade","priest","needle"]
		"reflections":plan=["mirror","mirror","fire","mirror","fire","mirror"]
		"facility_mana":plan=["mirror","fire","mirror","fire","mirror"]
		"interrupts":plan=["shield","javelin","shield","javelin","warden"]
		_:plan=["axe","spear","axe","spear","axe","spear","spear"]
	if p.queue.size()<2:
		var wanted: Dictionary={}
		for tail in plan:
			var id: String="unit."+p.faction+"."+str(tail)
			wanted[id]=int(wanted.get(id,0))+1
			if int(counts.get(id,0))<int(wanted[id]):s.request(0,"recruit",{"id":id});break
	if metric=="interrupts":
		for enemy in enemies:
			if float(enemy.get("windup",0))<=.08:continue
			for id in ["spell.shuang.lightning","spell.shuang.cold"]:
				if s.request(0,"cast",{"id":id,"target":enemy.uid,"x":enemy.x,"y":enemy.y}).ok:return
		return
	if metric=="summons":
		# Keep corpses for priests; invest mana in a persistent poison area
		# instead of consuming corpses or repeatedly buying single-target binds.
		for enemy in enemies:
			var nearby: int=0
			for other in enemies:
				if s.physical_point(enemy).distance_to(s.physical_point(other))<2:nearby+=1
			if nearby>=2:
				if s.request(0,"cast",{"id":"spell.mo.poison","x":enemy.x,"y":enemy.y}).ok:return
		return
	AI.cast_spells(s,0,enemies,allies,false)
func run():
	var db=Data.new();var records: Array=[]
	var args=OS.get_cmdline_user_args()
	for c in db.read_json("res://data/campaign.json").challenges:
		if args.has("--id") and c.id!=args[args.find("--id")+1]:continue
		var s=Simulation.new(db);s.start(c);s.ai_enabled=[false,true]
		var decision: float=0
		for i in range(181*60):
			if s.time>=decision:controller(s,c.challenge_rule.metric);decision=s.time+.15
			s.tick(1.0/60.0);s.drain_events()
			if s.winner!=-2:break
		var record={"id":c.id,"winner":s.winner,"time":s.time,"progress":s.ChallengeRules.progress(s),"target":c.challenge_rule.target,"score":s.ChallengeRules.score(s),"stats":s.stats[0],"reason":s.result_reason}
		records.append(record);print("CHALLENGE_STRATEGY ",JSON.stringify(record))
	var file=FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE)
	file.store_string(JSON.stringify({"scope":"Six legal-command strategies with normal economy, queue and formal fog; scripted 150ms decisions are feasibility evidence, not human usability proof.","inputs":{"ai":FileAccess.get_sha256("res://scripts/tactical_ai.gd"),"campaign":FileAccess.get_sha256("res://data/campaign.json"),"simulation":FileAccess.get_sha256("res://scripts/battle_sim.gd"),"controller":FileAccess.get_sha256("res://tests/probe_challenge_strategies.gd")},"records":records},"  "));file.close();quit()
func _initialize():call_deferred("run")
