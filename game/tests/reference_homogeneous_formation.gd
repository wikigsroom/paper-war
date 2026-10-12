extends "res://scripts/battle_sim.gd"
# Historical formation algorithm, isolated for before/after paid observations.
func update_ranged_formations():
	formation_ranges.clear()
	var groups: Dictionary={}
	for u in units:
		if u.hp<=0:continue
		var def: Dictionary=db.balance.units[u.id]
		if float(def.range)<=1.5 or not str(def.attack).begins_with("projectile"):continue
		var key: String=str(u.side)+"/"+str(u.edge)+"/"+str(u.id)
		if not groups.has(key):groups[key]=[]
		groups[key].append(u)
	for members in groups.values():
		var direction: float=1 if int(members[0].side)==0 else -1
		members.sort_custom(func(a,b):return int(a.uid)<int(b.uid) if is_equal_approx(float(a.s),float(b.s)) else float(a.s)*direction>float(b.s)*direction)
		for i in range(members.size()):
			var rear: int=0
			for j in range(i+1,mini(i+5,members.size())):
				if absf(float(members[i].s)-float(members[j].s))<=6:rear+=1
			var def: Dictionary=db.balance.units[members[i].id]
			var spacing: float=.72 if def.get("role","")=="colossus" else .54
			formation_ranges[members[i].uid]=maxf(minf(1.8,float(def.range)),float(def.range)-spacing*rear)
