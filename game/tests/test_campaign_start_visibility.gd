extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var checks: int=0
var failures: Array=[]
func verify(value: bool,note: String):
	checks+=1
	if not value:failures.append(note)
func run():
	var db=Data.new()
	for level in db.campaign:
		var s=Simulation.new(db);s.start(level);s.ai_enabled=[false,false]
		verify(s.visibility.point_visible(0,s.bases[0]),"own base sight "+level.id)
		if level.win=="protect":
			var target: Dictionary=s.actor(s.protected_uid)
			verify(not target.is_empty() and target.get("prebuilt",false),"authored protection target exists "+level.id)
			verify(s.visible_to(0,target),"own protection facility provides sight "+level.id)
			verify(s.slot_anchor(0,int(target.slot)).get("types",["tower","mana"]).has("tower"),"protection remains on military site "+level.id)
		for side in range(2):
			var site: Dictionary=s.side_sites(side).filter(func(a):return a.id=="site."+str(side)+".home-mana")[0]
			verify(s.visibility.point_visible(side,site),"rear mana site initially reachable "+level.id+str(side))
		s.tick(1.0/60.0)
		verify(s.winner==-2,"no missing-target instant loss "+level.id)
	print("CAMPAIGN_START_VISIBILITY: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
