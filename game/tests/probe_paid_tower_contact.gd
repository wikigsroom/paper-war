extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var records: Array=[]
	for faction in ["yin","mu","jin"]:
		for route in ["ground.2","bridge"]:
			var s=Simulation.new(db);s.start({"map":"map.01.04","faction":faction,"enemy":"mo","starting_gold":300,"enemy_starting_gold":300,"full_tech":true,"seed":137});s.ai_enabled=[false,false];s.units.clear()
			var result: Dictionary=s.request(1,"recruit",{"id":"unit.mo.blade"})
			if not result.ok:push_error("Scout purchase failed");quit(1);return
			var slot: int=-1
			for i in range(s.side_sites(1).size()):
				if s.side_sites(1)[i].get("types",[]).has("tower"):slot=i;break
			if slot<0:push_error("No tower site");quit(1);return
			for step in range(30*60):
				s.tick(1.0/60.0);s.drain_events()
				if s.visibility.point_visible(1,s.slot_anchor(1,slot)):break
			result=s.request(1,"build",{"id":"building.mo.tower","slot":slot})
			if not result.ok:push_error("Paid tower build failed: "+str(result));quit(1);return
			for step in range(6*60):s.tick(1.0/60.0);s.drain_events()
			# Remove the paid scout to isolate tower contact; no free defender.
			s.units.clear();s.visibility.refresh()
			var tower: Dictionary=s.buildings[0]
			var unit_id: String="unit."+faction+"."+{"yin":"axe","mu":"guard","jin":"berserker"}[faction]
			var fork: Dictionary=s.map.fork_nodes(0)[0]
			s.request(0,"route",{"node":fork.node,"edge":route})
			result=s.request(0,"recruit",{"id":unit_id})
			if not result.ok:push_error("Paid attacker failed");quit(1);return
			var forecast: float=AI.tower_crossing_cost(s,0,tower.id,Vector2(tower.x,tower.y),route)
			var hits: Array=[];var u: Dictionary={};var first_contact: float=-1;var released: float=-1
			for step in range(100*60):
				s.tick(1.0/60.0)
				for actor in s.units:
					if actor.side==0 and actor.id==unit_id:u=actor
				for e in s.drain_events():
					if e.kind=="hit" and int(e.get("source_uid",0))==int(tower.uid):
						if first_contact<0:first_contact=s.time
						hits.append({"time":s.time,"amount":e.amount})
				if not u.is_empty() and released<0:released=s.time
				if not u.is_empty() and (u.hp<=0 or tower.hp<=0):break
			records.append({"faction":faction,"route":route,"tower_state":tower.state,"tower_hp":tower.hp,"unit_hp":u.get("hp",-1),"first_tower_hit":first_contact,"unit_released":released,"end":s.time,"tower_hits":hits,"forecast_strategy_cost":forecast,"gold_remaining":[s.players[0].gold,s.players[1].gold]})
	var report={"scope":"Paid scout reveals a real tower slot, tower builds normally with fog; scout then removed to isolate one paid attacker. Full tech, no AI/workers/spells/research costs; not a normal opening or faction balance.","records":records,"inputs":{}}
	for path in ["res://scripts/battle_sim.gd","res://scripts/tactical_ai.gd","res://scripts/unit_abilities.gd","res://data/maps.json","res://data/balance-prototype.json","res://tests/probe_paid_tower_contact.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var file=FileAccess.open(OS.get_cmdline_user_args()[0],FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close();print("PAID_TOWER_CONTACT ",records.size());quit()
