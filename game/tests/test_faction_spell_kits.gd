extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var db
var checks: int=0
var failures: Array=[]
func verify(value: bool,note: String):
	checks+=1
	if not value:failures.append(note)
func make(faction: String):
	var s=Simulation.new(db)
	s.start({"map":"map.01.01","faction":faction,"enemy":"mo","full_tech":true,"starting_gold":5000})
	s.ai_enabled=[false,false];s.units.clear();s.events.clear()
	return s
func actors(s):
	var a=s.spawn(s.players[0].roster[0],0,20);a.hp=a.max_hp*.5;a["speed_override"]=0.0
	var b=s.spawn("unit.mo.giant",1,22);b["speed_override"]=0.0
	s.visibility.refresh();return [a,b]
func step(s,seconds: float):
	for i in range(roundi(seconds*60)):s.tick(1.0/60.0)
func run():
	db=Data.new()
	var signatures: Array=[]
	for faction in db.FACTIONS:
		var signature: Array=[]
		for id in db.spell_ids(faction):
			var s=make(faction);var pair=actors(s);s.players[0].mana=100
			var tail: String=id.get_slice(".",2)
			var target: Dictionary=pair[0] if tail in ["repair","fury","sacrifice","protect","clone"] else pair[1]
			var definition: Dictionary=db.balance.spells[id]
			verify(not db.spell_hint(id).is_empty() and db.name_of(id)!=tail,"named mechanic "+id)
			var outcome: Dictionary=s.request(0,"cast",{"id":id,"x":target.x,"y":target.y,"target":target.uid})
			verify(outcome.ok,"visible real command "+id+str(outcome))
			step(s,.7)
			verify(s.stats[0].casts==1,"one manual cast "+id)
			var mechanics: Dictionary=definition.duplicate(true);mechanics.erase("name");mechanics.erase("hint")
			signature.append(mechanics)
		verify(not signatures.has(signature),"faction toolkit differs mechanically "+faction)
		signatures.append(signature)
	var s=make("ji");var pair=actors(s)
	pair[0]["reload_left"]=2.0;pair[0]["reload_pending"]=true
	s.players[0].mana=100;s.request(0,"cast",{"id":"spell.ji.repair","target":pair[0].uid})
	verify(pair[0].reload_left==0 and not pair[0].reload_pending,"mechanical repair resets reload")
	s=make("shuang");pair=actors(s);pair[1].windup=.6;pair[1].target=pair[0].uid
	s.players[0].mana=100;s.request(0,"cast",{"id":"spell.shuang.lightning","target":pair[1].uid})
	verify(pair[1].windup==0 and pair[1].statuses.has("stun"),"frost hammer interrupts giant")
	s=make("yin");pair=actors(s);s.players[0].mana=100
	s.request(0,"cast",{"id":"spell.yin.stamp","x":21,"y":0})
	var original: float=s.spell_areas[0].x;step(s,1.5)
	verify(s.spell_areas[0].x>original+1,"rolling seal advances on real path")
	s=make("deng");pair=actors(s);s.players[0].mana=100
	s.request(0,"cast",{"id":"spell.deng.guardian","x":23,"y":0})
	s.visibility.refresh()
	verify(s.location_visible(0,30,0),"scout lamp expands forward vision")
	for unit in s.units:unit.hp=0
	s.visibility.refresh();verify(s.location_visible(0,30,0),"lamp retains sight after its escort dies")
	step(s,9.2);verify(not s.location_visible(0,30,0),"lamp expires and retracts sight")
	s=make("mu");pair=actors(s);s.players[0].mana=100
	var ally=s.spawn(s.players[0].roster[0],0,22);ally.hp=10;ally["speed_override"]=0.0
	s.visibility.refresh();s.request(0,"cast",{"id":"spell.mu.burst","x":22,"y":0})
	var hp: float=ally.hp;step(s,.1)
	verify(ally.hp>hp,"growth garden heals allies")
	s=make("bai");pair=actors(s);s.players[0].mana=100
	s.request(0,"cast",{"id":"spell.bai.clone","target":pair[0].uid})
	var copies=s.units.filter(func(u):return u.clone)
	verify(copies.size()==1 and copies[0].ttl==14,"white reprint has independent lifetime")
	print("FACTION_SPELL_KITS: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
