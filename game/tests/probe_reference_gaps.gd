extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Sim=preload("res://scripts/battle_sim.gd")
var db
func _initialize():call_deferred("run")
func make(faction: String):
	var s=Sim.new(db)
	s.start({"map":"map.01.01","faction":faction,"enemy":"yin","full_tech":true})
	s.units.clear();s.ai_enabled=[false,false];s.players[0].mana=100
	return s
func run():
	db=Data.new()
	var evidence: Dictionary={}
	var s=make("yin")
	var a=s.spawn("unit.yin.hammer",0,20)
	var target=s.spawn("unit.yin.axe",1,20.3)
	a.windup=.4;a.anim="windup";a.anim_t=.1;a.cooldown=1.0
	var before: Dictionary={"windup":a.windup,"cooldown":a.cooldown}
	s.cast(0,"spell.yin.fury",a.x,a.uid,a.y)
	evidence["fury"]={"before":before,"after":{"windup":a.windup,"cooldown":a.cooldown},"damage_multiplier":1.4,"same_attack_timing":a.windup==before.windup and a.cooldown==before.cooldown}
	s=make("mo")
	var victim=s.spawn("unit.yin.axe",1,20)
	s.cast(0,"spell.mo.poison",victim.x,0,victim.y)
	var later=s.spawn("unit.yin.axe",1,20.1)
	s.tick(1.0/60)
	evidence["poison"]={"original_victim_poisoned":victim.statuses.has("poison"),"new_arrival_poisoned":later.statuses.has("poison"),"persistent_scheduled_fields":s.scheduled.size()}
	s=make("deng")
	s.players[0].mana=0
	evidence["facility_mana"]={"rate_without_facility":s.mana_rate(0)}
	s.tick(10)
	evidence.facility_mana["mana_after_10_seconds_without_facility"]=s.players[0].mana
	s=make("yin")
	evidence["outside_roster"]={"roster":s.players[0].roster,"recruit_guard":s.recruit(0,"unit.yin.guard"),"research_guard":s.research(0,"tech.yin.unit.guard")}
	var inputs: Dictionary={}
	for path in ["res://scripts/battle_sim.gd","res://scripts/unit_abilities.gd","res://data/balance-prototype.json","res://data/technology.json"]:inputs[path]=FileAccess.get_sha256(path)
	var args=OS.get_cmdline_user_args()
	FileAccess.open(args[args.find("--report")+1],FileAccess.WRITE).store_string(JSON.stringify({"version":"3.0.0-rc6","evidence":evidence,"inputs":inputs,"scope":"Controlled native simulation observations of current implementation. Not a measurement of original game timing."},"\t"))
	print(JSON.stringify(evidence));quit()
