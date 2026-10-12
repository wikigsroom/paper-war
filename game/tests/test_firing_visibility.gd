extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var checks: int=0
var failures: Array=[]
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func _initialize():call_deferred("run")
func run():
	var s=Simulation.new(Data.new())
	s.start({"map":"map.01.01","faction":"yin","enemy":"yin","full_tech":true,"starting_gold":1000})
	s.ai_enabled=[false,false];s.units.clear();s.buildings.clear()
	var worker=s.spawn("unit.yin.worker",0,12)
	var shooter=s.spawn("unit.yin.spear",1,16)
	var other=s.spawn("unit.yin.spear",1,16.7)
	s.visibility.refresh()
	check(not s.visible_to(0,shooter),"Worker cannot see beyond its natural sight")
	check(is_equal_approx(s.visibility.radius(worker),3.2),"Worker natural sight unchanged")
	var mana: float=s.players[0].mana
	check(not s.request(0,"cast",{"id":"spell.yin.lightning","x":shooter.x,"target":shooter.uid}).ok,"Hidden target rejects manual spell")
	check(s.players[0].mana==mana,"Hidden rejection does not charge mana")
	shooter.windup=.2;s.visibility.refresh()
	check(not s.visible_to(0,shooter),"Windup alone does not disclose shooter")
	s.attack(shooter,worker);s.visibility.refresh()
	check(s.projectiles.size()==1,"Real attack releases a projectile")
	check(s.visible_to(0,shooter),"Released hostile attack reveals source")
	check(s.visibility.enemies[0].has(shooter),"AI and renderer use the same visible source")
	check(not s.visible_to(0,other),"Flash does not expose surrounding formation")
	check(s.request(0,"cast",{"id":"spell.yin.lightning","x":shooter.x,"target":shooter.uid}).ok,"Defender can legally countercast after release")
	s.time+=1.5;s.visibility.refresh()
	check(not s.visible_to(0,shooter),"Exposure expires at exact deadline")
	check(s.visibility.firing_reveals[0].is_empty(),"Expired records are removed")
	s.visibility.reveal_attack(other,worker);other.hp=0
	var anchor=s.map.project(Vector2(other.x,other.y))
	s.units.erase(other);s.visibility.refresh()
	check(s.visibility.point_visible(0,anchor),"Dead shooter retains brief release-location visibility")
	s.time+=1.5;s.visibility.refresh()
	check(not s.visibility.point_visible(0,anchor),"Dead-source flash expires without permanent tracking")
	s.visibility.reveal_attack(shooter,worker);shooter.side=0;s.visibility.refresh()
	check(s.visibility.firing_reveals[0].is_empty(),"Ownership change clears hostile exposure")
	s.visibility.reveal_attack(shooter,worker)
	check(s.visibility.firing_reveals[0].is_empty(),"Friendly action grants no hostile flash")
	shooter.side=1;shooter.hp=100;shooter.statuses["stun"]={"left":1}
	s.collecting_attacks=true;s.attack(shooter,worker);s.release_attack_intents();s.collecting_attacks=false;s.visibility.refresh()
	check(not s.visible_to(0,shooter),"Cancelled stunned intent cannot reveal")
	shooter.statuses.clear()
	for id in s.db.balance.buildings:
		if float(s.db.balance.buildings[id].get("damage",0))<=0:continue
		var tower={"uid":9000,"id":id,"building":true,"side":1,"hp":100.0,"edge":shooter.edge,"s":shooter.s,"x":shooter.x,"y":shooter.y,"state":"active","statuses":{}}
		s.buildings.append(tower);s.visibility.refresh()
		check(not s.visible_to(0,tower),"Enemy tower does not reveal itself before firing")
		s.launch(tower,worker,10,0,1,0);s.visibility.refresh()
		check(s.visible_to(0,tower),"Tower projectile also exposes source")
		check(s.visibility.last_seen[0].has(tower.uid),"Exposed tower participates in timestamped building memory")
		s.time+=1.5;s.visibility.refresh()
		check(not s.visible_to(0,tower),"Tower firing sight expires normally")
		break
	print("FIRING_VISIBILITY: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
