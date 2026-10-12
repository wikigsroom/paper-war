extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func _initialize():call_deferred("run")
func run():
	var db=Data.new()
	var compositions=[{"name":"guards","ids":["guard","guard","guard","guard"]},{"name":"screen_seeds","ids":["guard","guard","poisoner","poisoner"]},{"name":"cleanse_support","ids":["guard","poisoner","medic"]}]
	var report={"scope":"Controlled preassembled formations, max 300 unit purchase gold per side; full tech, no research/production timing, workers, buildings, AI or spells. Not a normal opening or faction balance proof.","inputs":{},"records":[]}
	for path in ["res://scripts/battle_sim.gd","res://scripts/unit_abilities.gd","res://data/balance-prototype.json","res://tests/probe_mu_formations.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	for composition in compositions:
		for enemy_mix in ["blades", "corrupt_mix"]:
			for mu_side in [0,1]:
				var s=Simulation.new(db)
				s.start({"map":"map.01.01","faction":"mu" if mu_side==0 else "mo","enemy":"mo" if mu_side==0 else "mu","starting_gold":300,"enemy_starting_gold":300,"full_tech":true})
				s.ai_enabled=[false,false];s.units.clear();s.buildings.clear()
				var costs=[0,0]
				for side in [0,1]:
					var ids: Array=composition.ids if side==mu_side else (["blade","blade","blade","blade","blade","blade","blade"] if enemy_mix=="blades" else ["blade","blade","blade","blade","needle","needle"])
					var faction: String="mu" if side==mu_side else "mo"
					for i in range(ids.size()):
						var id="unit."+faction+"."+str(ids[i]);var cost: int=int(db.balance.units[id].gold)
						costs[side]+=cost;s.players[side].gold-=cost
						var center: float=(float(s.bases[0].x)+float(s.bases[1].x))*.5
						s.spawn(id,side,center-5-float(i)*.8 if side==0 else center+5+float(i)*.8)
					if costs[side]>300:push_error("Formation exceeds budget");quit(1);return
				var deaths: Array=[]
				for step in range(60*60):
					s.tick(1.0/60.0)
					for e in s.drain_events():
						if e.kind=="death":deaths.append({"time":s.time,"side":e.side,"id":e.id})
					if s.population(0,false)==0 or s.population(1,false)==0:break
				var sides: Array=[]
				for side in [0,1]:
					var hp: float=0
					for u in s.units:
						if u.side==side and u.hp>0:hp+=u.hp
					sides.append({"cost":costs[side],"survivors":s.population(side,false),"hp":hp,"healed":s.stats[side].healed})
				report.records.append({"formation":composition.name,"enemy_mix":enemy_mix,"mu_side":mu_side,"time":s.time,"sides":sides,"deaths":deaths})
	var file=FileAccess.open(OS.get_cmdline_user_args()[0],FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
	print("MU_FORMATION_OBSERVATIONS ",report.records.size());quit()
