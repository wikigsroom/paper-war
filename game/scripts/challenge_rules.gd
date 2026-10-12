extends RefCounted
# Shared by simulation, HUD and persistent scores; effective results, not clicks.
static func progress(sim) -> float:
	var rule: Dictionary=sim.config.get("challenge_rule",{})
	var metric: String=str(rule.get("metric",""))
	if metric=="time":return sim.time
	if metric=="facility_mana":return float(sim.stats[0].mana_income.get("facility",0))
	return float(sim.stats[0].get(metric,0))

static func evaluate(sim) -> bool:
	var rule: Dictionary=sim.config.get("challenge_rule",{})
	if rule.is_empty():return false
	if progress(sim)>=float(rule.target):
		sim.winner=0;sim.result_reason="挑战目标完成";return true
	if sim.time>=float(rule.get("deadline",180)):
		sim.winner=1;sim.result_reason="挑战时间结束，目标未完成";return true
	return false

static func text(sim) -> String:
	var rule: Dictionary=sim.config.get("challenge_rule",{})
	var remaining: int=maxi(0,int(ceilf(float(rule.get("deadline",180))-sim.time)))
	return str(rule.get("label","挑战"))+" %d / %d · 剩余 %d 秒"%[int(progress(sim)),int(rule.get("target",0)),remaining]

static func score(sim) -> int:
	if sim.winner!=0:return 0
	var rule: Dictionary=sim.config.get("challenge_rule",{})
	var remaining: float=maxf(0,float(rule.get("deadline",180))-sim.time)
	var health: float=clampf(sim.bases[0].hp/sim.bases[0].max_hp,0,1)
	return maxi(0,1000+int(remaining*10)+int(health*500)-int(sim.stats[0].lost)*15)

static func stars(sim) -> int:
	if sim.winner!=0:return 0
	var thresholds: Array=sim.config.get("challenge_rule",{}).get("star_scores",[1500,2000])
	var points: int=score(sim)
	return 1+(1 if points>=int(thresholds[0]) else 0)+(1 if points>=int(thresholds[1]) else 0)
