"""Freeze visible ranged-response policies without changing the shipped game."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/fielding-contact-rc25'
ap=argparse.ArgumentParser();ap.add_argument('--waiting',action='store_true');ap.add_argument('--side-control',action='store_true');args=ap.parse_args()
name='ranged-r3' if args.side_control else ('ranged-r2' if args.waiting else 'ranged-r1')
target=QA/(name+'-runtime');baseline=QA/'rc24-runtime'
assert not target.exists(), 'Never overwrite frozen candidates'
shutil.copytree(baseline,target)
path=target/'scripts/tactical_ai.gd';source=path.read_text('utf-8')
old='\t\tif grant_ready:best=grant_goal if p.unlocked.has(grant_goal) else ""\n'
enabled='fielding and int(sim.config.get("contact_counter_side",-1)) in [-1,side]' if args.side_control else 'fielding'
new=old+'\t\tvar counter: String=contact_ranged_offer(sim,side,allies,enemies) if '+enabled+' else ""\n'
new+='\t\tif counter!="" and (float(sim.db.balance.units[counter].gold)<=p.gold or '+('true' if args.waiting else 'false')+'):\n'
new+='\t\t\tvar affordable: bool=float(sim.db.balance.units[counter].gold)<=p.gold\n'
new+='\t\t\tif affordable or contact_counter_delivery_due(sim,side,counter,enemies):\n'
new+='\t\t\t\tbest=counter;p.ai_research="";p.ai_build_reserve=0.0\n'
assert source.count(old)==1;source=source.replace(old,new)
helper='''
# Respond to a currently observed ranged engagement with an unlocked weapon
# that can reach that opponent. These queries do not pay or consume RNG.
static func contact_ranged_offer(sim,side: int,allies: Array,enemies: Array) -> String:
	var p: Dictionary=sim.players[side]
	var own: Array=allies.filter(func(u):return u.side==side and u.hp>0 and not sim.db.balance.units[u.id].get("economy",false))
	var visible: Array=enemies.filter(func(u):return u.side!=side and u.hp>0 and sim.visible_to(side,u) and not sim.db.balance.units[u.id].get("economy",false))
	if spawn_camped(sim,side,visible):return ""
	var targets: Array=[]
	for enemy in visible:
		var weapon: Dictionary=sim.db.balance.units[enemy.id]
		if float(weapon.range)<=1.5 or not str(weapon.attack).begins_with("projectile"):continue
		var fighting: bool=own.any(func(u):return sim.combat_distance(enemy,u,weapon)<=float(weapon.range)+.3)
		if not fighting and not economic_attack(sim,side,enemy):continue
		var covered: bool=own.any(func(u):return str(sim.db.balance.units[u.id].attack).begins_with("projectile") and float(sim.db.balance.units[u.id].range)>=float(weapon.range) and sim.combat_distance(u,enemy,sim.db.balance.units[u.id])<=float(sim.db.balance.units[u.id].range)+.3)
		if not covered:targets.append(enemy)
	var best: String="";var best_cost: float=INF
	for enemy in targets:
		var range_needed: float=float(sim.db.balance.units[enemy.id].range)
		if p.queue.any(func(id):return str(sim.db.balance.units[id].attack).begins_with("projectile") and float(sim.db.balance.units[id].range)>=range_needed):continue
		for id in p.roster:
			if not p.unlocked.has(id):continue
			var weapon: Dictionary=sim.db.balance.units[id]
			if not str(weapon.attack).begins_with("projectile") or float(weapon.range)<range_needed or not weapon.get("manual_recruit",true):continue
			if float(weapon.gold)<best_cost:best=id;best_cost=float(weapon.gold)
	return best

# Only actual carried cargo already coming home may justify a brief wait.
# It remains a forecast for withholding a purchase, never spendable currency.
static func contact_counter_delivery_due(sim,side: int,id: String,enemies: Array) -> bool:
	var def: Dictionary=sim.db.balance.units[id]
	var need: float=float(def.gold)-float(sim.players[side].gold)
	if need<=0:return true
	if immediate_economic_threat(sim,side,enemies,float(def.production_seconds)):return false
	var returning: float=0
	for worker in sim.units:
		if worker.side!=side or worker.hp<=0 or not sim.db.balance.units[worker.id].get("economy",false) or int(worker.cargo)<=0 or worker.job!="deliver":continue
		if worker.statuses.has("root") or worker.statuses.has("bind") or worker.statuses.has("stun") or worker.statuses.has("cold"):continue
		var path: Dictionary=sim.map.route_to(worker,sim.bases[side])
		var travel: float=INF if path.is_empty() else float(path.distance)/maxf(.1,float(sim.db.balance.units[worker.id].speed))
		if travel+maxf(0,1.0-float(worker.job_time))<=3.0:returning+=float(worker.cargo)
	return returning>=need

'''
marker='static func unbuilt_facility_reserve(sim,side: int) -> float:\n'
assert source.count(marker)==1;source=source.replace(marker,helper+marker)
path.write_text(source,'utf-8')
diff=QA/(name+'.diff')
diff.write_text(''.join(difflib.unified_diff((baseline/'scripts/tactical_ai.gd').read_text('utf-8').splitlines(keepends=True),source.splitlines(keepends=True),fromfile='rc24/tactical_ai.gd',tofile=name+'/tactical_ai.gd')),'utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(target/'candidate.json').write_text(json.dumps({'policy':name,'baseline':'3.0.0-rc24-preview','shipping_source_changed':False,
    'waiting_for_real_carried_cargo':args.waiting,'side_control':args.side_control,'prices_times_roads_fog_unchanged':True,
    'baseline_ai_sha256':sha(baseline/'scripts/tactical_ai.gd'),'ai_sha256':sha(path),'diff_sha256':sha(diff),
    'generator_sha256':sha(Path(__file__))},indent=2),'utf-8')
print('Frozen ranged response prepared:',name)
