extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var checks: int=0
var failures: Array=[]
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func make(db):
	var s=Simulation.new(db)
	s.start({"map":"map.01.04","faction":"mu","enemy":"yin","starting_gold":0})
	s.ai_enabled=[false,false];s.units.clear();s.players[0].mana=50;s.time=20
	return s
func solo_control(db):
	# Controlled combat coordinates and windups isolate spell utility. These
	# fixtures prove costs/visibility/interrupts, never normal battle balance.
	for kit in [{"faction":"mu","tail":"bind","unit":"guard"},{"faction":"mo","tail":"bind","unit":"blade"},{"faction":"jin","tail":"bind","unit":"berserker"},{"faction":"yin","tail":"lightning","unit":"axe"},{"faction":"bai","tail":"root","unit":"mirror"},{"faction":"mo","tail":"convert","unit":"blade"}]:
		var faction: String=str(kit.faction)
		for side in [0,1]:
			var modes: Array=["lethal","nonlethal","hidden","short_mana","cooldown"]
			if kit.tail=="lightning":modes.append("surviving_lightning")
			for mode in modes:
				var s=Simulation.new(db)
				s.start({"map":"map.01.04","faction":faction if side==0 else "yin","enemy":"yin" if side==0 else faction,"starting_gold":0,"enemy_starting_gold":0})
				s.ai_enabled=[false,false];s.units.clear();s.time=20
				var spell: String="spell."+faction+"."+str(kit.tail)
				var own: String="unit."+faction+"."+str(kit.unit)
				var midpoint: float=(float(s.bases[0].x)+float(s.bases[1].x))*.5
				var ally=s.spawn(own,side,midpoint)
				var enemy_x: float=float(s.bases[1-side].x) if mode=="hidden" else midpoint+(.65 if side==0 else -.65)
				var enemy=s.spawn("unit.yin.axe",1-side,enemy_x)
				ally.hp=ally.max_hp if mode=="nonlethal" else 10.0
				enemy.windup=.2;enemy.target=ally.uid
				if kit.tail=="lightning" and mode=="lethal":enemy.hp=80.0
				var p: Dictionary=s.players[side]
				# A single available ability removes competing spell priorities.
				p.unlocked=[spell]
				var fee: float=float(db.balance.spells[spell].mana)
				p.mana=fee-1 if mode=="short_mana" else fee
				if mode=="cooldown":p.cooldowns[spell]=2.0
				s.visibility.refresh();s.drain_events()
				var note: String=spell+" / "+str(side)+" / "+str(mode)
				verify(float(db.balance.units[enemy.id].gold)<95 and AI.dist(enemy,s.bases[side])>9 and s.visible_to(side,enemy)==(mode!="hidden") and not AI.economic_attack(s,side,enemy),"Solo fixture excludes price/base/miner/multiple-target triggers: "+note)
				var before: float=float(p.mana)
				AI.cast_spells(s,side,[enemy],[ally],false)
				var cast: bool=mode=="lethal" and kit.tail!="root"
				verify(s.stats[side].casts==(1 if cast else 0) and s.stats[side].spell_counts.get(spell,0)==(1 if cast else 0),"Only the visible affordable ready lethal attack receives control: "+note)
				verify(is_equal_approx(float(p.mana),before-(fee if cast else 0)),"Solo response pays exactly its normal mana cost: "+note)
				verify((enemy.hp<=0 or enemy.windup==0) if cast else (enemy.hp>0 and is_equal_approx(float(enemy.windup),.2)),"Solo response interrupts without inventing an unavailable cast: "+note)
func run():
	var db=Data.new();var s=make(db)
	var ally=s.spawn("unit.mu.guard",0,20)
	var first=s.spawn("unit.yin.axe",1,22);var second=s.spawn("unit.yin.spear",1,25)
	s.visibility.refresh();AI.cast_spells(s,0,[first,second],[ally],false)
	verify(s.players[0].mana==10 and s.stats[0].spell_counts.get("spell.mu.poison",0)==1,"spaced visible formation already fits a real field; pay 40 instead of treating it as future-only")
	s=make(db);ally=s.spawn("unit.mu.guard",0,20)
	first=s.spawn("unit.yin.axe",1,22);second=s.spawn("unit.yin.spear",1,22.8)
	s.players[0].mana=40;s.visibility.refresh()
	AI.cast_spells(s,0,[first,second],[ally],false)
	verify(s.stats[0].spell_counts.get("spell.mu.poison",0)==1 and s.players[0].mana==0,"converged formation also pays exactly the full field price")
	s=make(db);ally=s.spawn("unit.mu.guard",0,20)
	first=s.spawn("unit.yin.axe",1,22);second=s.spawn("unit.yin.spear",1,25)
	s.players[0].cooldowns["spell.mu.poison"]=8;s.visibility.refresh()
	AI.cast_spells(s,0,[first,second],[ally],false)
	verify(s.stats[0].spell_counts.get("spell.mu.bind",0)==1 and s.players[0].mana==20,"long-cooldown field does not lock routine control budget")
	s=make(db);s.players[0].unlocked=["spell.mu.bind"]
	ally=s.spawn("unit.mu.guard",0,20);first=s.spawn("unit.yin.axe",1,22);second=s.spawn("unit.yin.spear",1,25)
	s.visibility.refresh();AI.cast_spells(s,0,[first,second],[ally],false)
	verify(s.players[0].mana==20 and s.stats[0].casts==1,"locked field cannot reserve mana")
	s=make(db);ally=s.spawn("unit.mu.guard",0,20);ally.hp=15
	first=s.spawn("unit.yin.axe",1,20.6);second=s.spawn("unit.yin.spear",1,24)
	first.windup=.2;first.target=ally.uid;s.visibility.refresh()
	AI.cast_spells(s,0,[first,second],[ally],false)
	verify(first.statuses.has("bind") and first.windup==0 and s.players[0].mana==20,"visible lethal windup releases reserve for a paid emergency interrupt")
	s=make(db);ally=s.spawn("unit.mu.guard",0,20)
	first=s.spawn("unit.mu.colossus",1,21);second=s.spawn("unit.yin.spear",1,25)
	first.windup=.6;first.target=ally.uid;s.visibility.refresh()
	AI.cast_spells(s,0,[first,second],[ally],false)
	verify(first.windup==0 and s.stats[0].spell_counts.get("spell.mu.bind",0)==1,"heavy attack window has priority over formation savings")
	s=make(db);ally=s.spawn("unit.mu.guard",0,20);first=s.spawn("unit.jin.berserker",1,21)
	second=s.spawn("unit.yin.spear",1,39);s.visibility.refresh()
	verify(not s.visible_to(0,second),"second enemy is actually hidden")
	AI.turn(s,0)
	verify(s.stats[0].spell_counts.get("spell.mu.bind",0)==1 and s.players[0].mana==20,"hidden formation member cannot induce field savings")
	s=make(db);s.players[0].mana=70;s.players[0].cooldowns["spell.mu.poison"]=.5
	ally=s.spawn("unit.mu.guard",0,20);first=s.spawn("unit.yin.axe",1,22);second=s.spawn("unit.yin.spear",1,25)
	s.visibility.refresh();AI.cast_spells(s,0,[first,second],[ally],false)
	verify(s.players[0].mana==40 and second.statuses.has("bind"),"surplus mana may fund control without consuming the formation budget")
	s=make(db);s.players[0].cooldowns["spell.mu.poison"]=.5
	ally=s.spawn("unit.mu.guard",0,20);first=s.spawn("unit.yin.axe",1,22);second=s.spawn("unit.yin.spear",1,25)
	s.visibility.refresh();AI.cast_spells(s,0,[first,second],[ally],false)
	verify(s.stats[0].casts==0 and s.players[0].mana==50,"almost ready field may save budget for the imminent window")
	solo_control(db)
	print("AI_SPELL_BUDGET: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
