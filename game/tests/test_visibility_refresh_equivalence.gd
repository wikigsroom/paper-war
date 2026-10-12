extends SceneTree

const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const SpellRules=preload("res://scripts/manual_spell_rules.gd")

var checks: int=0
var failures: Array=[]
const STEP: float=1.0/60.0

func _initialize():call_deferred("run")

func verify(value: bool,note: String):
	checks+=1
	if not value and failures.size()<12:failures.append(note)

func actor_signature(actor: Dictionary) -> Dictionary:
	var out: Dictionary={}
	for key in ["uid","id","side","hp","max_hp","x","y","edge","s","age","cooldown","windup","target","hurt","anim","anim_t","walk","facing","special_cd","summon_cd","owner","clone","ttl","cargo","job","job_time","mine","ability_clock","control_clock","attack_serial","death_processed","death_queued","statuses"]:
		if actor.has(key):out[key]=actor[key]
	return out

func state_signature(sim: Simulation) -> Dictionary:
	var players: Array=[]
	for player in sim.players:
		players.append({"faction":player.faction,"gold":player.gold,"mana":player.mana,"unlocked":player.unlocked,"studied":player.studied,"queue":player.queue,"production":player.production,"research":player.research,"cooldowns":player.cooldowns,"sequence":player.sequence,"preferred_mine":player.get("preferred_mine","")})
	var units: Array=[]
	for actor in sim.units:units.append(actor_signature(actor))
	var buildings: Array=[]
	for actor in sim.buildings:buildings.append(actor_signature(actor))
	var bases: Array=[]
	for actor in sim.bases:bases.append(actor_signature(actor))
	return {"time":sim.time,"tick_count":sim.tick_count,"winner":sim.winner,"players":players,"units":units,"buildings":buildings,"bases":bases,"projectiles":sim.projectiles,"scheduled":sim.scheduled,"spell_areas":sim.spell_areas,"corpses":sim.corpses,"events":sim.events,"current":sim.visibility.current,"explored":sim.visibility.explored,"visible":sim.visibility.visible_uids,"last_seen":sim.visibility.last_seen,"spotted":sim.visibility.spotted,"firing":sim.visibility.firing_reveals,"routes":sim.map.choices}

func compare(cached: Simulation,forced: Simulation,label: String):
	verify(JSON.stringify(state_signature(cached))==JSON.stringify(state_signature(forced)),label+" public state")
	verify(cached.rng.state==forced.rng.state,label+" rng")
	for side in range(2):
		verify(cached.ai_rng[side].state==forced.ai_rng[side].state,label+" ai rng "+str(side))
		verify(cached.visibility.enemies[side].map(func(a):return int(a.uid))==forced.visibility.enemies[side].map(func(a):return int(a.uid)),label+" enemy order "+str(side))

func tick_pair(cached: Simulation,forced: Simulation,steps: int,label: String):
	for step in range(steps):
		cached.tick(STEP);forced.tick(STEP)
		# Reference path: the historical unconditional refresh after every tick.
		forced.visibility.refresh()
		compare(cached,forced,label+" tick "+str(step))
		cached.drain_events();forced.drain_events()
		if not failures.is_empty():return

func inject_zone(sim: Simulation,id: String,anchor: Dictionary,data: Dictionary,definition: Dictionary={}):
	SpellRules.zone(sim,0,id,float(anchor.x),float(anchor.y),data,definition)
	sim.visibility.refresh()

func run():
	var db: Data=Data.new()
	var options={"map":"map.01.04","faction":"yin","enemy":"mo","full_tech":true,"seed":137,"starting_gold":1000,"enemy_starting_gold":1000}
	var cached: Simulation=Simulation.new(db);var forced: Simulation=Simulation.new(db)
	cached.start(options);forced.start(options)
	cached.ai_enabled=[true,true];forced.ai_enabled=[true,true]
	compare(cached,forced,"initial")
	tick_pair(cached,forced,120,"ordinary paid AI")
	verify(cached.visibility.revision<forced.visibility.revision,"ordinary cache lowers rebuild count")

	var stationary_options={"map":"map.01.04","faction":"yin","enemy":"mo","full_tech":true,"seed":419,"starting_gold":1000,"enemy_starting_gold":1000}
	cached=Simulation.new(db);forced=Simulation.new(db)
	cached.start(stationary_options);forced.start(stationary_options)
	cached.ai_enabled=[false,false];forced.ai_enabled=[false,false]
	tick_pair(cached,forced,60,"idle")
	verify(cached.visibility.revision+30<forced.visibility.revision,"idle cache skips redundant rebuilds")
	for sim in [cached,forced]:sim.spawn("unit.yin.axe",0,sim.bases[0].x+2.0)
	for sim in [cached,forced]:sim.visibility.refresh()
	tick_pair(cached,forced,20,"spawn sight")

	var anchor: Dictionary=cached.map.anchor("ground.2",3.0)
	for sim in [cached,forced]:inject_zone(sim,"qa.delayed-vision",anchor,{"duration":.30,"radius":0.0,"vision":6.0,"speed":0.0,"period":.5,"status":"","potency":0.0},{"delay":.10})
	tick_pair(cached,forced,30,"delayed vision")
	anchor=cached.map.anchor("ground.2",3.0)
	for sim in [cached,forced]:inject_zone(sim,"qa.moving-vision",anchor,{"duration":.50,"radius":0.0,"vision":6.0,"speed":1.5,"period":.5,"status":"","potency":0.0})
	tick_pair(cached,forced,30,"moving vision")

	var victim_c: Dictionary=cached.spawn("unit.mo.blade",1,20.0)
	var victim_f: Dictionary=forced.spawn("unit.mo.blade",1,20.0)
	var victim_anchor: Dictionary=cached.physical_anchor(victim_c)
	for sim in [cached,forced]:
		sim.set_status(sim.actor(victim_c.uid),"bind",2.0,0,0)
		inject_zone(sim,"qa.knockback",victim_anchor,{"duration":.30,"radius":1.8,"vision":0.0,"speed":0.0,"period":.1,"status":"","potency":0.0},{"zone_knockback":.35})
	tick_pair(cached,forced,20,"zone displacement")
	for sim in [cached,forced]:
		var doomed: Dictionary=sim.actor(victim_c.uid)
		if not doomed.is_empty():sim.die(doomed,false)
	tick_pair(cached,forced,4,"unit death")

	print("VISIBILITY_REFRESH_EQUIVALENCE: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
