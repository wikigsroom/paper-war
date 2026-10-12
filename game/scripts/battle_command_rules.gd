extends RefCounted
# Pure command gates shared by the authority and the owned client projection.
# No payment, timers, events or opponent-private data are read or modified here.
static func research_error(sim,side: int,id: String) -> String:
	var p: Dictionary=sim.players[side]
	var node: Dictionary=sim.db.tech(id)
	if node.is_empty() or node.faction!=p.faction:return "无法研究此科技"
	if node.grant.begins_with("unit.") and not p.roster.has(node.grant):return "此兵种未加入本局部署编组"
	if p.studied.has(id):return "科技已经完成"
	if not p.research.is_empty():return "研究中，请等待完成"
	for required in node.requires:
		if not p.studied.has(required):return "请先完成前置科技"
	if p.gold<float(node.gold):return "研究金币不足"
	return ""

static func facility_error(sim,side: int,id: String) -> String:
	var p: Dictionary=sim.players[side]
	if not sim.db.balance.buildings.has(id) or not p.unlocked.has(id) or id.get_slice(".",1)!=p.faction:return "需要先研究此建筑"
	if id.ends_with(".base"):return "基地不可重复建造"
	if id.ends_with(".mana"):
		var count: int=0
		for b in sim.buildings:
			if b.side==side and b.hp>0 and b.id.ends_with(".mana"):count+=1
		if count>=int(sim.db.balance.economy.get("max_mana_facilities",2)):return "产法设施已达到上限"
	if p.gold<float(sim.db.balance.buildings[id].gold):return "建造金币不足"
	return ""

static func occupied(sim,side: int,slot: int) -> bool:
	for b in sim.buildings:
		if b.side==side and b.slot==slot and b.hp>0:return true
	return false

static func site_error(sim,side: int,id: String,slot: int) -> String:
	if slot<0 or slot>=sim.side_sites(side).size():return "请选择有效建筑位"
	var types: Array=sim.slot_anchor(side,slot).get("types",["tower","mana"])
	if not types.has(id.get_slice(".",2)):return "这个位置仅能建造"+("纸哨塔" if types==["tower"] else "产法纸灯")
	return ""

static func build_error(sim,side: int,id: String,slot: int,mission_setup: bool=false) -> String:
	if slot<0 or slot>=sim.side_sites(side).size():return "请选择有效建筑位"
	if not mission_setup and not sim.visibility.point_visible(side,sim.slot_anchor(side,slot)):return "请先侦察此建筑位"
	var error: String=site_error(sim,side,id,slot)
	if not error.is_empty():return error
	var p: Dictionary=sim.players[side]
	if not sim.db.balance.buildings.has(id) or not p.unlocked.has(id) or id.get_slice(".",1)!=p.faction:return "需要先研究此建筑"
	if id.ends_with(".base"):return "基地不可重复建造"
	if occupied(sim,side,slot):return "该建筑位已占用"
	return facility_error(sim,side,id)

static func build_selection_error(sim,side: int,id: String,slot: int=-1) -> String:
	# Selecting a blueprint does not charge or construct. An unseen compatible
	# site may be selected for navigation; the actual build still requires vision.
	if slot>=0:
		var site: String=site_error(sim,side,id,slot)
		if not site.is_empty():return site
		if occupied(sim,side,slot):return "该建筑位已占用"
	else:
		var available: bool=false
		for i in range(sim.side_sites(side).size()):
			if site_error(sim,side,id,i).is_empty() and not occupied(sim,side,i):available=true;break
		if not available:return "没有兼容的空闲建造位"
	return facility_error(sim,side,id)
